import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from aether.api import app
from aether.config import settings
from aether.ir.models import Universe
from aether.jobs import JobStore
from aether.storage.db import AetherDB
from aether.worker import execute_next


def test_job_progress_lifecycle(tmp_path):
    store = JobStore(tmp_path / "aether.db")
    job = store.create()
    store.update(job.id, 22, "Sampling git history")
    mid = store.get(job.id)
    assert mid is not None
    assert mid.percent == 22
    assert mid.stage == "Sampling git history"
    store.finish(job.id, {"universe_id": "abc"})
    done = store.get(job.id)
    assert done is not None
    assert done.status == "done"
    assert done.percent == 100
    assert done.result["universe_id"] == "abc"
    store.conn.close()


def test_job_list_newest_first(tmp_path):
    store = JobStore(tmp_path / "aether.db")
    older = store.create(label="first")
    newer = store.create(label="second")
    store.update(older.id, 10, "Parsing")
    rows = store.list(limit=10)
    assert [row.id for row in rows] == [newer.id, older.id]
    assert rows[1].label == "first"
    assert rows[1].percent == 10
    assert rows[0].created_at
    assert len(store.list(limit=1)) == 1
    store.conn.close()


def test_jobs_survive_a_new_process(tmp_path):
    path = tmp_path / "aether.db"
    first = JobStore(path)
    job = first.create(label="keep")
    first.update(job.id, 15, "Cloning")
    first.conn.close()

    second = JobStore(path)
    again = second.get(job.id)
    assert again is not None
    assert again.percent == 15
    assert again.label == "keep"
    assert again.stage == "Cloning"
    second.conn.close()


def test_dead_worker_is_requeued(tmp_path):
    path = tmp_path / "aether.db"
    store = JobStore(path)
    job = store.create(label="half")
    store.conn.execute(
        "UPDATE jobs SET status = 'running', stage = 'Parsing', percent = 40, owner_pid = ? WHERE id = ?",
        (99_999_999, job.id),
    )
    assert store.requeue_interrupted() == 1
    again = store.get(job.id)
    assert again is not None
    assert again.status == "queued"
    assert again.percent == 0

    live = store.create(label="live")
    claimed = store.claim()
    assert claimed is not None
    assert claimed.id == job.id
    assert store.requeue_interrupted() == 0
    assert store.get(job.id).status == "running"
    assert store.get(live.id).status == "queued"
    store.conn.close()


def test_worker_stamps_the_org(tmp_path, monkeypatch):
    path = tmp_path / "aether.db"
    store = JobStore(path)
    db = AetherDB(path)
    seen: dict[str, str] = {}

    def fake_build(req, database, on_progress=None, data_dir=None, org_id="", actor=""):
        seen["org_id"] = org_id
        universe = Universe(id="jobbed", repo_path="/tmp/jobbed", org_id=org_id)
        database.upsert_universe(universe)
        on_progress(30, "Parsing")
        return universe, []

    monkeypatch.setattr("aether.worker.build_universe", fake_build)
    store.create(label="/tmp/jobbed", org_id="org-9", request={"path": "/tmp/jobbed"})
    assert execute_next(store, db) is True
    done = store.get(store.list(limit=1)[0].id)
    assert done is not None
    assert done.status == "done"
    assert seen["org_id"] == "org-9"
    stored = db.get_universe("jobbed")
    assert stored is not None
    assert stored.org_id == "org-9"
    store.conn.close()
    db.conn.close()


def test_api_queues_without_running_ingest(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    called: list[str] = []

    def fake_build(*_args, **_kwargs):
        called.append("ran")
        raise AssertionError("the API process must not clone or parse")

    monkeypatch.setattr("aether.worker.build_universe", fake_build)
    with TestClient(app) as client:
        queued = client.post("/v1/jobs", json={"path": "/tmp/aether-not-here"})
        assert queued.status_code == 200
        body = queued.json()
        assert body["status"] == "queued"
        fetched = client.get(f"/v1/jobs/{body['job_id']}")
        assert fetched.json()["status"] == "queued"
    assert called == []


def test_worker_process_records_a_missing_path(tmp_path):
    path = tmp_path / "aether.db"
    store = JobStore(path)
    job = store.create(label="/tmp/aether-p503-missing", request={"path": "/tmp/aether-p503-missing"})
    store.conn.close()

    env = os.environ.copy()
    env["AETHER_DATA_DIR"] = str(tmp_path)
    env["AETHER_INGEST_WORKER"] = "0"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    proc = subprocess.run(
        [sys.executable, "-m", "aether.worker", "--once"],
        env=env,
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    again = JobStore(path)
    done = again.get(job.id)
    assert done is not None
    assert done.status == "error"
    assert "does not exist" in done.error
    again.conn.close()
