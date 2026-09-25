import pytest
from fastapi.testclient import TestClient

from aether.acquisition.git_ingest import IngestRequest, clone_percent, ingest_repo
from aether.api import app
from aether.config import settings
from aether import api as api_mod
from aether.physics.time_machine import build_timeline, narrative_from_labels, pressure_band
from tests.test_physics import _snap


def test_clone_percent_moves_inside_clone_slice():
    assert clone_percent("Receiving objects:   0% (1/10)") == 8
    assert clone_percent("Receiving objects:  50% (5/10)") == 12
    assert clone_percent("Resolving deltas: 100% (10/10)") == 16
    assert clone_percent("remote: enumerating objects") is None


def test_source_and_size_caps_reject(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")
    monkeypatch.setattr(settings, "max_source_files", 1)
    with pytest.raises(ValueError, match="source files"):
        ingest_repo(IngestRequest(path=str(tmp_path)))

    monkeypatch.setattr(settings, "max_source_files", 50000)
    monkeypatch.setattr(settings, "max_clone_bytes", 4)
    with pytest.raises(ValueError, match="bytes"):
        ingest_repo(IngestRequest(path=str(tmp_path)))


def test_snapshot_cap_warns(monkeypatch):
    fixture = __import__("pathlib").Path(__file__).resolve().parents[2] / "fixtures" / "polyglot-debt"
    monkeypatch.setattr(settings, "max_snapshots", 1)
    _repo = ingest_repo(IngestRequest(path=str(fixture), max_samples=1))
    assert len(_repo.samples) == 1
    assert any("sampling 1" in warning for warning in _repo.warnings)


def test_pressure_band_is_a_point_at_now_and_widens_later():
    assert pressure_band(1.2, 0.0, 0.0) == (1.2, 1.2)
    lo, hi = pressure_band(1.2, 2.0, 24.0)
    assert hi - lo >= 0.6
    assert lo <= 1.2 <= hi


def test_default_caps_accept_polyglot_fixture():
    fixture = __import__("pathlib").Path(__file__).resolve().parents[2] / "fixtures" / "polyglot-debt"
    ingested = ingest_repo(IngestRequest(path=str(fixture)))
    assert ingested.license == "MIT"
    assert len(ingested.samples) >= 2
    assert not any("above the cap" in warning for warning in ingested.warnings)


def test_heuristic_timeline_pressure_unchanged_and_banded():
    snaps = [
        _snap("a", "2024-01-01T00:00:00+00:00"),
        _snap("b", "2025-01-01T00:00:00+00:00"),
    ]
    frames = build_timeline(snaps, 24, velocity=2.0)
    labeled = build_timeline(snaps, 24, velocity=2.0, pattern_labels=["god_module"])
    assert [c.pressure for c in frames[0].cells] == [c.pressure for c in labeled[0].cells]
    assert frames[0].narrative == labeled[0].narrative
    assert "predicted" not in frames[0].narrative
    for cell in frames[0].cells:
        assert cell.pressure_lo <= cell.pressure <= cell.pressure_hi
    assert labeled[-1].narrative_kind == "rising_pressure"
    assert "god module" in labeled[-1].narrative
    kind, text = narrative_from_labels(["cyclic_dep"], 8, "stable", "keep")
    assert kind == "bottleneck"
    assert "cycle" in text


def test_cancel_job_sticks(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    with TestClient(app) as client:
        assert api_mod.job_store is not None
        store = api_mod.job_store
        store.clear()
        job = store.create(label="demo")
        store.update(job.id, 12, "Cloning repository")
        cancelled = client.post(f"/v1/jobs/{job.id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        assert cancelled.json()["stage"] == "cancelled"
        store.update(job.id, 80, "Parsing snapshot")
        store.finish(job.id, {"universe_id": "nope"})
        stuck = store.get(job.id)
        assert stuck is not None
        assert stuck.status == "cancelled"
        assert stuck.percent == 12
        missing = client.post("/v1/jobs/missing/cancel")
        assert missing.status_code == 404
