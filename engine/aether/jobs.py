from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

Status = Literal["queued", "running", "done", "error", "cancelled"]
ProgressFn = Callable[[int, str], None]


@dataclass
class Job:
    id: str
    status: Status = "queued"
    percent: int = 0
    stage: str = "queued"
    error: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    label: str = ""
    seq: int = 0
    org_id: str = ""
    request: dict[str, Any] = field(default_factory=dict)
    owner_pid: int = 0


class IngestCancelled(Exception):
    """Raised when a running ingest sees a cancel request."""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class JobStore:
    """SQLite queue. A new process opened on the same file sees the same jobs."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(path), timeout=30, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._init()

    def _init(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                percent INTEGER NOT NULL,
                stage TEXT NOT NULL,
                error TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL,
                label TEXT NOT NULL,
                seq INTEGER NOT NULL,
                org_id TEXT NOT NULL DEFAULT '',
                request TEXT NOT NULL DEFAULT '{}',
                owner_pid INTEGER NOT NULL DEFAULT 0
            )
            """
        )

    def create(self, label: str = "", org_id: str = "", request: dict[str, Any] | None = None) -> Job:
        job = Job(
            id=uuid.uuid4().hex[:12],
            created_at=datetime.now(timezone.utc).isoformat(),
            label=label,
            org_id=org_id,
            request=dict(request or {}),
        )
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                seq = int(self.conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM jobs").fetchone()[0])
                job.seq = seq
                self._insert(job)
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
        return job

    def _insert(self, job: Job) -> None:
        self.conn.execute(
            """
            INSERT INTO jobs
            (id, status, percent, stage, error, result, created_at, label, seq, org_id, request, owner_pid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.status,
                job.percent,
                job.stage,
                job.error,
                json.dumps(job.result),
                job.created_at,
                job.label,
                job.seq,
                job.org_id,
                json.dumps(job.request),
                job.owner_pid,
            ),
        )

    def get(self, job_id: str) -> Job | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return self._row(row)

    def list(self, limit: int = 20, org_id: str | None = None) -> list[Job]:
        cap = max(1, min(limit, 100))
        if org_id is None:
            rows = self.conn.execute(
                "SELECT * FROM jobs ORDER BY seq DESC LIMIT ?",
                (cap,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM jobs WHERE org_id = ? ORDER BY seq DESC LIMIT ?",
                (org_id, cap),
            ).fetchall()
        return [self._row(row) for row in rows]

    def clear(self) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM jobs")

    def claim(self) -> Job | None:
        """Mark the oldest queued job running for this process. One claim wins."""
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                row = self.conn.execute(
                    "SELECT * FROM jobs WHERE status = 'queued' ORDER BY seq ASC LIMIT 1"
                ).fetchone()
                if not row:
                    self.conn.execute("COMMIT")
                    return None
                cur = self.conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'running', stage = 'running', owner_pid = ?
                    WHERE id = ? AND status = 'queued'
                    """,
                    (os.getpid(), row["id"]),
                )
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
        if cur.rowcount != 1:
            return None
        job = self._row(row)
        job.status = "running"
        job.stage = "running"
        job.owner_pid = os.getpid()
        return job

    def requeue_interrupted(self) -> int:
        """Queue jobs whose worker process is gone, so a restart finishes them."""
        rows = self.conn.execute(
            "SELECT id, owner_pid FROM jobs WHERE status = 'running'"
        ).fetchall()
        moved = 0
        for row in rows:
            if _pid_alive(int(row["owner_pid"])):
                continue
            cur = self.conn.execute(
                """
                UPDATE jobs
                SET status = 'queued', stage = 'queued', percent = 0, owner_pid = 0
                WHERE id = ? AND status = 'running'
                """,
                (row["id"],),
            )
            moved += cur.rowcount
        return moved

    def is_cancelled(self, job_id: str) -> bool:
        row = self.conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return bool(row and row["status"] == "cancelled")

    def cancel(self, job_id: str) -> bool:
        cur = self.conn.execute(
            """
            UPDATE jobs SET status = 'cancelled', stage = 'cancelled'
            WHERE id = ? AND status NOT IN ('done', 'error', 'cancelled')
            """,
            (job_id,),
        )
        return cur.rowcount == 1

    def update(self, job_id: str, percent: int, stage: str, status: Status = "running") -> None:
        self.conn.execute(
            """
            UPDATE jobs SET status = ?, percent = ?, stage = ?
            WHERE id = ? AND status NOT IN ('cancelled', 'done', 'error')
            """,
            (status, max(0, min(100, percent)), stage, job_id),
        )

    def finish(self, job_id: str, result: dict[str, Any]) -> None:
        self.conn.execute(
            """
            UPDATE jobs
            SET status = 'done', percent = 100, stage = 'done', result = ?, owner_pid = 0
            WHERE id = ? AND status != 'cancelled'
            """,
            (json.dumps(result), job_id),
        )

    def fail(self, job_id: str, error: str) -> None:
        self.conn.execute(
            """
            UPDATE jobs
            SET status = 'error', stage = 'failed', error = ?, owner_pid = 0
            WHERE id = ? AND status != 'cancelled'
            """,
            (error, job_id),
        )

    def _row(self, row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            status=row["status"],
            percent=int(row["percent"]),
            stage=row["stage"],
            error=row["error"],
            result=json.loads(row["result"] or "{}"),
            created_at=row["created_at"],
            label=row["label"],
            seq=int(row["seq"]),
            org_id=row["org_id"],
            request=json.loads(row["request"] or "{}"),
            owner_pid=int(row["owner_pid"]),
        )
