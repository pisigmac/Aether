import sqlite3

from fastapi.testclient import TestClient

from aether.api import app
from aether.config import settings
from aether.ir.models import Universe
from aether.storage.db import AetherDB
from tests.test_auth import _enable, _keys, _token
from tests.test_physics import _snap


def _seed(db_path, universe_id: str, org_id: str) -> None:
    db = AetherDB(db_path)
    snaps = [_snap("a", "2025-01-01T00:00:00+00:00"), _snap("b", "2026-01-01T00:00:00+00:00")]
    db.upsert_universe(
        Universe(
            id=universe_id,
            repo_path=f"/tmp/{universe_id}",
            snapshots=snaps,
            org_id=org_id,
        )
    )
    db.conn.close()


def test_list_get_delete_stay_open_without_opendesk(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    _seed(tmp_path / "aether.db", "owned", "org-1")
    _seed(tmp_path / "aether.db", "other", "org-2")

    with TestClient(app) as client:
        listed = client.get("/v1/universes")
        assert listed.status_code == 200
        ids = {row["id"] for row in listed.json()}
        assert ids == {"owned", "other"}
        assert client.get("/v1/universes/other").status_code == 200
        removed = client.delete("/v1/universes/other")
        assert removed.status_code == 204
        assert client.get("/v1/universes/other").status_code == 404
        assert client.get("/v1/universes/owned").json()["org_id"] == "org-1"


def test_signed_in_org_cannot_see_another_org(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    private_pem, public_pem = _keys()
    _enable(monkeypatch, public_pem)
    _seed(tmp_path / "aether.db", "mine", "org-1")
    _seed(tmp_path / "aether.db", "theirs", "org-2")
    mine = {"Authorization": f"Bearer {_token(private_pem)}"}
    theirs = {"Authorization": f"Bearer {_token(private_pem, org_id='org-2')}"}

    with TestClient(app) as client:
        assert client.get("/v1/universes").status_code == 401
        listed = client.get("/v1/universes", headers=mine).json()
        assert [row["id"] for row in listed] == ["mine"]
        assert client.get("/v1/universes/theirs", headers=mine).status_code == 404
        assert client.delete("/v1/universes/theirs", headers=mine).status_code == 404
        assert client.get("/v1/universes/theirs/forecast", headers=mine).status_code == 404
        assert client.get("/v1/universes/mine/forecast", headers=mine).status_code == 200
        assert client.delete("/v1/universes/mine", headers=mine).status_code == 204
        assert client.get("/v1/universes/theirs", headers=theirs).json()["id"] == "theirs"


def test_create_records_the_org(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    private_pem, public_pem = _keys()
    _enable(monkeypatch, public_pem)

    def fake_build(req, db, on_progress=None, data_dir=None, org_id="", actor=""):
        universe = Universe(id="made", repo_path="/tmp/made", org_id=org_id)
        db.upsert_universe(universe)
        return universe, []

    monkeypatch.setattr("aether.api.build_universe", fake_build)
    headers = {"Authorization": f"Bearer {_token(private_pem)}"}
    with TestClient(app) as client:
        created = client.post("/v1/universes", json={"path": "/tmp/made"}, headers=headers)
        assert created.status_code == 200
        body = client.get("/v1/universes/made", headers=headers).json()
        assert body["org_id"] == "org-1"


def test_job_queue_is_scoped_to_the_org(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    private_pem, public_pem = _keys()
    _enable(monkeypatch, public_pem)
    mine = {"Authorization": f"Bearer {_token(private_pem)}"}
    theirs = {"Authorization": f"Bearer {_token(private_pem, org_id='org-2')}"}
    with TestClient(app) as client:
        queued = client.post("/v1/jobs", json={"path": "/tmp/mine"}, headers=mine)
        assert queued.status_code == 200
        job_id = queued.json()["job_id"]
        assert client.get("/v1/jobs", headers=theirs).json() == []
        assert client.get(f"/v1/jobs/{job_id}", headers=theirs).status_code == 404
        assert client.post(f"/v1/jobs/{job_id}/cancel", headers=theirs).status_code == 404
        visible = client.get("/v1/jobs", headers=mine).json()
        assert [row["job_id"] for row in visible] == [job_id]
        assert client.get(f"/v1/jobs/{job_id}", headers=mine).json()["status"] == "queued"


def test_legacy_database_gains_an_org_column(tmp_path):
    path = tmp_path / "aether.db"
    payload = Universe(id="old", repo_path="/tmp/old").model_dump_json()
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE universes (
            id TEXT PRIMARY KEY,
            repo_path TEXT NOT NULL,
            license TEXT,
            velocity REAL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO universes (id, repo_path, license, velocity, payload) VALUES (?, ?, ?, ?, ?)",
        ("old", "/tmp/old", "", 1.0, payload),
    )
    conn.commit()
    conn.close()

    db = AetherDB(path)
    rows = db.list_universes()
    assert rows[0]["org_id"] == ""
    assert db.list_universes("org-1") == []
    db.conn.close()
