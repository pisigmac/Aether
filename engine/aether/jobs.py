from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


class IngestCancelled(Exception):
    """Raised when a running ingest sees a cancel request."""


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._seq = 0

    def create(self, label: str = "") -> Job:
        with self._lock:
            self._seq += 1
            job = Job(
                id=uuid.uuid4().hex[:12],
                created_at=datetime.now(timezone.utc).isoformat(),
                label=label,
                seq=self._seq,
            )
            self._jobs[job.id] = job
            return self._copy(job)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return self._copy(job)

    def list(self, limit: int = 20) -> list[Job]:
        cap = max(1, min(limit, 100))
        with self._lock:
            rows = sorted(self._jobs.values(), key=lambda job: (job.created_at, job.seq), reverse=True)
            return [self._copy(job) for job in rows[:cap]]

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._seq = 0

    def _copy(self, job: Job) -> Job:
        return Job(
            id=job.id,
            status=job.status,
            percent=job.percent,
            stage=job.stage,
            error=job.error,
            result=dict(job.result),
            created_at=job.created_at,
            label=job.label,
            seq=job.seq,
        )

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job.status == "cancelled")

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status in {"done", "error", "cancelled"}:
                return False
            job.status = "cancelled"
            job.stage = "cancelled"
            return True

    def update(self, job_id: str, percent: int, stage: str, status: Status = "running") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status in {"cancelled", "done", "error"}:
                return
            job.status = status
            job.percent = max(0, min(100, percent))
            job.stage = stage

    def finish(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status == "cancelled":
                return
            job.status = "done"
            job.percent = 100
            job.stage = "done"
            job.result = result

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status == "cancelled":
                return
            job.status = "error"
            job.stage = "failed"
            job.error = error


store = JobStore()
