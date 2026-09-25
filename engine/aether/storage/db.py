from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from aether.config import settings
from aether.ir.models import ChangeSet, EvolutionRecord, ForecastBundle, Snapshot, Universe

_SCHEMA = """
CREATE TABLE IF NOT EXISTS universes (
    id TEXT PRIMARY KEY,
    repo_path TEXT NOT NULL,
    license TEXT,
    velocity REAL,
    payload TEXT NOT NULL,
    org_id TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS snapshots (
    universe_id TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    authored_at TEXT,
    snapshot_hash TEXT,
    payload TEXT NOT NULL,
    PRIMARY KEY (universe_id, commit_sha)
);
CREATE TABLE IF NOT EXISTS evolution (
    repo_id TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    authored_at TEXT,
    snapshot_hash TEXT,
    payload TEXT NOT NULL,
    PRIMARY KEY (repo_id, commit_sha)
);
CREATE TABLE IF NOT EXISTS changesets (
    id TEXT PRIMARY KEY,
    universe_id TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS forecasts (
    universe_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id TEXT PRIMARY KEY,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    org_id TEXT NOT NULL DEFAULT '',
    target TEXT NOT NULL,
    license TEXT NOT NULL,
    decision TEXT NOT NULL,
    universe_id TEXT NOT NULL DEFAULT ''
);
"""


class AetherDB:
    def __init__(self, path: Path | None = None, *, url: str = "") -> None:
        self.url = url
        self.dialect = "postgres" if url else "sqlite"
        self.path = path
        self._lock = threading.Lock()
        if url:
            self.conn = _postgres(url)
        else:
            if path is None:
                raise ValueError("SQLite storage needs a path")
            path.parent.mkdir(parents=True, exist_ok=True)
            self.path = path
            self.conn = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA busy_timeout=5000")
        self._init()

    def _init(self) -> None:
        if self.dialect == "sqlite":
            self.conn.executescript(_SCHEMA)
            self._ensure_org_column()
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.commit()
            return
        for statement in _SCHEMA.split(";"):
            if statement.strip():
                self.conn.execute(statement)
        self.conn.commit()

    def _ensure_org_column(self) -> None:
        cols = {row["name"] for row in self.conn.execute("PRAGMA table_info(universes)")}
        if "org_id" not in cols:
            self.conn.execute("ALTER TABLE universes ADD COLUMN org_id TEXT NOT NULL DEFAULT ''")

    def _sql(self, sql: str) -> str:
        if self.dialect == "postgres":
            return sql.replace("?", "%s")
        return sql

    def _exec(self, sql: str, params: tuple = ()):
        return self.conn.execute(self._sql(sql), params)

    def _upsert(self, table: str, columns: tuple[str, ...], conflict: tuple[str, ...], values: tuple) -> None:
        cols = ", ".join(columns)
        marks = ", ".join(["?"] * len(columns))
        if self.dialect == "sqlite":
            sql = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({marks})"
        else:
            sets = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns if col not in conflict)
            sql = (
                f"INSERT INTO {table} ({cols}) VALUES ({marks}) "
                f"ON CONFLICT ({', '.join(conflict)}) DO UPDATE SET {sets}"
            )
        self._exec(sql, values)

    def upsert_universe(self, universe: Universe) -> None:
        with self._lock:
            try:
                self._upsert(
                    "universes",
                    ("id", "repo_path", "license", "velocity", "payload", "org_id"),
                    ("id",),
                    (
                        universe.id,
                        universe.repo_path,
                        universe.license,
                        universe.velocity_commits_per_week,
                        universe.model_dump_json(),
                        universe.org_id,
                    ),
                )
                for snap in universe.snapshots:
                    self._upsert(
                        "snapshots",
                        ("universe_id", "commit_sha", "authored_at", "snapshot_hash", "payload"),
                        ("universe_id", "commit_sha"),
                        (
                            universe.id,
                            snap.commit_sha,
                            snap.authored_at,
                            snap.snapshot_hash,
                            snap.model_dump_json(),
                        ),
                    )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def get_universe(self, universe_id: str) -> Universe | None:
        with self._lock:
            row = self._exec("SELECT payload FROM universes WHERE id = ?", (universe_id,)).fetchone()
        if not row:
            return None
        return Universe.model_validate_json(row["payload"])

    def list_universes(self, org_id: str | None = None) -> list[dict]:
        sql = "SELECT id, repo_path, license, velocity, org_id FROM universes"
        params: tuple[str, ...] = ()
        if org_id is not None:
            sql += " WHERE org_id = ?"
            params = (org_id,)
        with self._lock:
            rows = self._exec(sql, params).fetchall()
        return [dict(row) for row in rows]

    def delete_universe(self, universe_id: str) -> None:
        with self._lock:
            try:
                self._exec("DELETE FROM universes WHERE id = ?", (universe_id,))
                self._exec("DELETE FROM snapshots WHERE universe_id = ?", (universe_id,))
                self._exec("DELETE FROM evolution WHERE repo_id = ?", (universe_id,))
                self._exec("DELETE FROM changesets WHERE universe_id = ?", (universe_id,))
                self._exec("DELETE FROM forecasts WHERE universe_id = ?", (universe_id,))
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def upsert_evolution(self, record: EvolutionRecord) -> None:
        with self._lock:
            try:
                self._upsert(
                    "evolution",
                    ("repo_id", "commit_sha", "authored_at", "snapshot_hash", "payload"),
                    ("repo_id", "commit_sha"),
                    (
                        record.repo_id,
                        record.commit_sha,
                        record.authored_at,
                        record.snapshot_hash,
                        record.model_dump_json(),
                    ),
                )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def list_evolution(self, repo_id: str) -> list[EvolutionRecord]:
        with self._lock:
            rows = self._exec(
                "SELECT payload FROM evolution WHERE repo_id = ? ORDER BY authored_at",
                (repo_id,),
            ).fetchall()
        return [EvolutionRecord.model_validate_json(row["payload"]) for row in rows]

    def list_all_evolution(self) -> list[EvolutionRecord]:
        with self._lock:
            rows = self._exec("SELECT payload FROM evolution ORDER BY authored_at").fetchall()
        return [EvolutionRecord.model_validate_json(row["payload"]) for row in rows]

    def upsert_changeset(self, changeset: ChangeSet) -> None:
        with self._lock:
            try:
                self._upsert(
                    "changesets",
                    ("id", "universe_id", "payload"),
                    ("id",),
                    (changeset.id, changeset.universe_id, changeset.model_dump_json()),
                )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def list_changesets(self, universe_id: str) -> list[ChangeSet]:
        with self._lock:
            rows = self._exec(
                "SELECT payload FROM changesets WHERE universe_id = ?",
                (universe_id,),
            ).fetchall()
        return [ChangeSet.model_validate_json(row["payload"]) for row in rows]

    def upsert_forecast(self, bundle: ForecastBundle) -> None:
        with self._lock:
            try:
                self._upsert(
                    "forecasts",
                    ("universe_id", "payload"),
                    ("universe_id",),
                    (bundle.universe_id, bundle.model_dump_json()),
                )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def get_forecast(self, universe_id: str) -> ForecastBundle | None:
        with self._lock:
            row = self._exec(
                "SELECT payload FROM forecasts WHERE universe_id = ?",
                (universe_id,),
            ).fetchone()
        if not row:
            return None
        return ForecastBundle.model_validate_json(row["payload"])

    def get_snapshot(self, universe_id: str, commit_sha: str) -> Snapshot | None:
        with self._lock:
            row = self._exec(
                "SELECT payload FROM snapshots WHERE universe_id = ? AND commit_sha = ?",
                (universe_id, commit_sha),
            ).fetchone()
        if not row:
            return None
        return Snapshot.model_validate_json(row["payload"])

    def append_audit(
        self,
        *,
        actor: str,
        org_id: str,
        target: str,
        license_id: str,
        decision: str,
        universe_id: str = "",
    ) -> None:
        with self._lock:
            try:
                self._exec(
                    """
                    INSERT INTO audit (id, at, actor, org_id, target, license, decision, universe_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uuid.uuid4().hex[:12],
                        datetime.now(timezone.utc).isoformat(),
                        actor or "local",
                        org_id or "",
                        target,
                        license_id,
                        decision,
                        universe_id,
                    ),
                )
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def list_audit(self, org_id: str | None = None, limit: int = 50) -> list[dict]:
        cap = max(1, min(limit, 200))
        sql = "SELECT id, at, actor, org_id, target, license, decision, universe_id FROM audit"
        params: tuple = (cap,)
        if org_id is not None:
            sql += " WHERE org_id = ?"
            params = (org_id, cap)
        sql += " ORDER BY at DESC, id DESC LIMIT ?"
        with self._lock:
            rows = self._exec(sql, params).fetchall()
        return [dict(row) for row in rows]


def open_database(path: Path | None = None) -> AetherDB:
    """Postgres when AETHER_DATABASE_URL is set. Otherwise the SQLite file."""
    if settings.database_url:
        return AetherDB(url=settings.database_url)
    return AetherDB(path or (settings.data_dir / "aether.db"))


def _postgres(url: str):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("Postgres storage needs the psycopg package") from exc
    return psycopg.connect(url, row_factory=dict_row)
