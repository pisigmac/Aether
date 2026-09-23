from fastapi.testclient import TestClient

from aether.api import app
from aether.config import settings
from aether.jobs import store as job_store
from aether.ir.models import ChangeSet, Mutation, Node, NodeKind, Universe
from aether.physics.predictor import train_linear
from aether.storage.db import AetherDB
from tests.test_phase2 import _growing_records
from tests.test_physics import _snap


def _universe(db_path) -> None:
    db = AetherDB(db_path)
    snaps = [_snap("a", "2025-01-01T00:00:00+00:00"), _snap("b", "2026-01-01T00:00:00+00:00")]
    db.upsert_universe(Universe(id="u1", repo_path="/tmp/x", snapshots=snaps, velocity_commits_per_week=2))
    db.conn.close()


def test_forecast_mode_toggle_does_not_clobber_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "model_path", None)
    _universe(tmp_path / "aether.db")

    with TestClient(app) as client:
        auto = client.get("/v1/universes/u1/forecast")
        assert auto.status_code == 200
        assert auto.json()["heuristic"] is True
        cached = auto.json()["warnings"][0]

        missing = client.get("/v1/universes/u1/forecast?mode=learned")
        assert missing.status_code == 409

        heur = client.get("/v1/universes/u1/forecast?mode=heuristic")
        assert heur.status_code == 200
        assert heur.json()["heuristic"] is True

        again = client.get("/v1/universes/u1/forecast")
        assert again.json()["warnings"][0] == cached
        assert again.json()["heuristic"] is True

        predictor = client.get("/v1/predictor")
        assert predictor.status_code == 200
        assert predictor.json()["learned_available"] is False


def test_forecast_learned_mode_same_changeset(tmp_path, monkeypatch):
    model_path = tmp_path / "model.json"
    train_linear(_growing_records(8)).save(model_path)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "model_path", model_path)
    _universe(tmp_path / "aether.db")
    db = AetherDB(tmp_path / "aether.db")
    db.upsert_changeset(
        ChangeSet(
            id="cs1",
            universe_id="u1",
            label="add-god",
            mutations=[
                Mutation(
                    op="add",
                    node=Node(
                        id="god",
                        kind=NodeKind.MODULE,
                        path="big.py",
                        export_name="big.py",
                        loc=400,
                        complexity=50,
                    ),
                )
            ],
        )
    )
    db.conn.close()

    with TestClient(app) as client:
        heur = client.get("/v1/universes/u1/forecast?mode=heuristic")
        learned = client.get("/v1/universes/u1/forecast?mode=learned")
        assert heur.status_code == 200
        assert learned.status_code == 200
        assert heur.json()["heuristic"] is True
        assert learned.json()["heuristic"] is False
        assert heur.json()["universe_id"] == learned.json()["universe_id"]
        assert any("add-god" in w for w in heur.json()["warnings"])
        assert any("add-god" in w for w in learned.json()["warnings"])
        assert heur.json()["ghosts"] and learned.json()["ghosts"]
        info = client.get("/v1/predictor").json()
        assert info["learned_available"] is True
        stored = client.get("/v1/universes/u1/forecast").json()
        assert stored["heuristic"] is False
        again = client.get("/v1/universes/u1/forecast?mode=heuristic")
        assert again.json()["heuristic"] is True
        cached = client.get("/v1/universes/u1/forecast").json()
        assert cached["heuristic"] is False


def test_list_jobs_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    job_store.clear()
    try:
        job = job_store.create(label="../fixtures/polyglot-debt")
        job_store.update(job.id, 40, "Parsing snapshot 1/4")
        with TestClient(app) as client:
            rows = client.get("/v1/jobs").json()
            found = next(row for row in rows if row["job_id"] == job.id)
            assert found["percent"] == 40
            assert found["stage"] == "Parsing snapshot 1/4"
            assert found["label"] == "../fixtures/polyglot-debt"
            assert found["created_at"]
            one = client.get(f"/v1/jobs/{job.id}")
            assert one.status_code == 200
            assert one.json()["job_id"] == job.id
    finally:
        job_store.clear()
