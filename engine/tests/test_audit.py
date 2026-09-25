from fastapi.testclient import TestClient

from aether.api import app
from aether.config import settings
from aether.jobs import JobStore
from aether.storage.db import AetherDB
from aether.worker import execute_next
from tests.test_auth import _enable, _keys, _token


def test_rejected_license_is_audited(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    root = tmp_path / "gpl"
    root.mkdir()
    (root / "package.json").write_text('{"license": "GPL-3.0"}\n', encoding="utf-8")
    with TestClient(app) as client:
        denied = client.post("/v1/universes", json={"path": str(root)})
        assert denied.status_code == 403
        rows = client.get("/v1/audit").json()
    assert rows[0]["decision"] == "rejected"
    assert rows[0]["license"] == "GPL-3.0"
    assert rows[0]["actor"] == "local"
    assert rows[0]["target"] == str(root)
    assert rows[0]["at"]


def test_audit_is_scoped_to_the_org(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    private_pem, public_pem = _keys()
    _enable(monkeypatch, public_pem)
    root = tmp_path / "gpl"
    root.mkdir()
    (root / "package.json").write_text('{"license": "GPL-3.0"}\n', encoding="utf-8")
    mine = {"Authorization": f"Bearer {_token(private_pem)}"}
    theirs = {"Authorization": f"Bearer {_token(private_pem, org_id='org-2', email='bea@example.com')}"}
    with TestClient(app) as client:
        denied = client.post("/v1/universes", json={"path": str(root)}, headers=mine)
        assert denied.status_code == 403
        assert client.get("/v1/audit").status_code == 401
        visible = client.get("/v1/audit", headers=mine).json()
        assert visible[0]["actor"] == "ada@example.com"
        assert visible[0]["org_id"] == "org-1"
        assert client.get("/v1/audit", headers=theirs).json() == []


def test_worker_records_the_actor(tmp_path, monkeypatch):
    path = tmp_path / "aether.db"
    store = JobStore(path)
    db = AetherDB(path)
    seen: dict[str, str] = {}

    def fake_build(req, database, on_progress=None, data_dir=None, org_id="", actor=""):
        seen["actor"] = actor
        seen["org_id"] = org_id
        raise RuntimeError("stop")

    monkeypatch.setattr("aether.worker.build_universe", fake_build)
    store.create(
        label="/tmp/x",
        org_id="org-9",
        request={"path": "/tmp/x", "_actor": "ada@example.com"},
    )
    assert execute_next(store, db) is True
    failed = store.list(limit=1)[0]
    assert failed.status == "error"
    assert seen == {"actor": "ada@example.com", "org_id": "org-9"}
    store.conn.close()
    db.conn.close()
