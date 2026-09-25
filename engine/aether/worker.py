"""Ingest worker. Clone and parse run here, not in the API process."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from aether.acquisition.git_ingest import IngestRequest
from aether.config import settings
from aether.jobs import IngestCancelled, JobStore
from aether.pipeline import build_universe
from aether.storage.db import AetherDB, open_database


def run_job(
    store: JobStore,
    db: AetherDB,
    job_id: str,
    req: IngestRequest,
    org_id: str,
    actor: str = "",
) -> None:
    store.update(job_id, 2, "Starting ingest")

    def on_progress(percent: int, stage: str) -> None:
        if store.is_cancelled(job_id):
            raise IngestCancelled()
        store.update(job_id, percent, stage)

    try:
        universe, warnings = build_universe(
            req, db, on_progress=on_progress, org_id=org_id, actor=actor
        )
        if not store.is_cancelled(job_id):
            store.finish(
                job_id,
                {
                    "universe_id": universe.id,
                    "repo_path": universe.repo_path,
                    "license": universe.license,
                    "snapshots": len(universe.snapshots),
                    "velocity_commits_per_week": universe.velocity_commits_per_week,
                    "sample_policy": universe.sample_policy,
                    "warnings": warnings,
                },
            )
    except IngestCancelled:
        store.cancel(job_id)
    except Exception as exc:
        store.fail(job_id, str(exc))


def execute_next(store: JobStore, db: AetherDB) -> bool:
    job = store.claim()
    if job is None:
        return False
    body = job.request or {}
    req = IngestRequest(
        path=str(body.get("path") or ""),
        url=str(body.get("url") or ""),
        pr_ref=str(body.get("pr_ref") or ""),
        velocity_override=body.get("velocity_override"),
        sample_policy=str(body.get("sample_policy") or "even"),
        sample_every=int(body.get("sample_every") or 1),
    )
    run_job(store, db, job.id, req, job.org_id, actor=str(body.get("_actor") or ""))
    return True


def serve(once: bool = False) -> None:
    path = settings.data_dir / "aether.db"
    store = JobStore(path)
    db = open_database(path)
    store.requeue_interrupted()
    if once:
        execute_next(store, db)
        return
    while True:
        if not execute_next(store, db):
            time.sleep(0.4)


def spawn() -> subprocess.Popen:
    env = os.environ.copy()
    env["AETHER_DATA_DIR"] = str(settings.data_dir)
    env["AETHER_INGEST_WORKER"] = "0"
    return subprocess.Popen([sys.executable, "-m", "aether.worker"], env=env)


def main() -> None:
    serve(once="--once" in sys.argv[1:])


if __name__ == "__main__":
    main()
