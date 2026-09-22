from __future__ import annotations

import sqlite3
from pathlib import Path

from aether.ir.models import ChangeSet, EvolutionRecord, ForecastBundle, Snapshot, Universe


class AetherDB:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS universes (
                id TEXT PRIMARY KEY,
                repo_path TEXT NOT NULL,
                license TEXT,
                velocity REAL,
                payload TEXT NOT NULL
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
            """
        )
        self.conn.commit()

    def upsert_universe(self, universe: Universe) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO universes (id, repo_path, license, velocity, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                universe.id,
                universe.repo_path,
                universe.license,
                universe.velocity_commits_per_week,
                universe.model_dump_json(),
            ),
        )
        for snap in universe.snapshots:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO snapshots
                (universe_id, commit_sha, authored_at, snapshot_hash, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    universe.id,
                    snap.commit_sha,
                    snap.authored_at,
                    snap.snapshot_hash,
                    snap.model_dump_json(),
                ),
            )
        self.conn.commit()

    def get_universe(self, universe_id: str) -> Universe | None:
        row = self.conn.execute(
            "SELECT payload FROM universes WHERE id = ?", (universe_id,)
        ).fetchone()
        if not row:
            return None
        return Universe.model_validate_json(row["payload"])

    def list_universes(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, repo_path, license, velocity FROM universes"
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_evolution(self, record: EvolutionRecord) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO evolution
            (repo_id, commit_sha, authored_at, snapshot_hash, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.repo_id,
                record.commit_sha,
                record.authored_at,
                record.snapshot_hash,
                record.model_dump_json(),
            ),
        )
        self.conn.commit()

    def list_evolution(self, repo_id: str) -> list[EvolutionRecord]:
        rows = self.conn.execute(
            "SELECT payload FROM evolution WHERE repo_id = ? ORDER BY authored_at",
            (repo_id,),
        ).fetchall()
        return [EvolutionRecord.model_validate_json(r["payload"]) for r in rows]

    def upsert_changeset(self, changeset: ChangeSet) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO changesets (id, universe_id, payload) VALUES (?, ?, ?)",
            (changeset.id, changeset.universe_id, changeset.model_dump_json()),
        )
        self.conn.commit()

    def list_changesets(self, universe_id: str) -> list[ChangeSet]:
        rows = self.conn.execute(
            "SELECT payload FROM changesets WHERE universe_id = ?",
            (universe_id,),
        ).fetchall()
        return [ChangeSet.model_validate_json(r["payload"]) for r in rows]

    def upsert_forecast(self, bundle: ForecastBundle) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO forecasts (universe_id, payload) VALUES (?, ?)",
            (bundle.universe_id, bundle.model_dump_json()),
        )
        self.conn.commit()

    def get_forecast(self, universe_id: str) -> ForecastBundle | None:
        row = self.conn.execute(
            "SELECT payload FROM forecasts WHERE universe_id = ?",
            (universe_id,),
        ).fetchone()
        if not row:
            return None
        return ForecastBundle.model_validate_json(row["payload"])

    def get_snapshot(self, universe_id: str, commit_sha: str) -> Snapshot | None:
        row = self.conn.execute(
            "SELECT payload FROM snapshots WHERE universe_id = ? AND commit_sha = ?",
            (universe_id, commit_sha),
        ).fetchone()
        if not row:
            return None
        return Snapshot.model_validate_json(row["payload"])
