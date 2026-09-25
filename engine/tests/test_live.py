from fastapi.testclient import TestClient

from aether import api as api_mod
from aether.config import settings
from aether.ir.models import ForecastBundle, NodeMetrics, TimelineFrame, Universe
from aether.live import forecast_reading, headline, job_targets_repo, pick_universe_id, pressure_band
from aether.storage.db import AetherDB
from tests.test_physics import _snap


def test_pressure_bands():
    assert pressure_band(0.2) == "calm"
    assert pressure_band(0.8) == "watch"
    assert pressure_band(1.2) == "high-pressure"


def test_pick_universe_prefers_exact_path_and_unique_name():
    rows = [("a", "/data/clones/abc"), ("b", "/work/Aether")]
    assert pick_universe_id(rows, "/work/Aether") == "b"
    assert pick_universe_id(rows, "/work/Aether/") == "b"
    assert pick_universe_id(rows, "/other/Aether") == "b"
    assert pick_universe_id([("a", "/tmp/app"), ("b", "/opt/app")], "/src/app") == ""
    assert pick_universe_id(rows, "") == ""


def test_job_targets_repo_by_path_or_name():
    assert job_targets_repo("/work/Aether", "", "", "/work/Aether")
    assert job_targets_repo("", "/work/Aether", "", "/tmp/Aether")
    assert not job_targets_repo("/work/pandas", "", "", "/work/Aether")


def test_forecast_reading_uses_month_eight_and_hides_nothing():
    bundle = ForecastBundle(
        universe_id="u1",
        repo_path="/work/Aether",
        horizon_months=24,
        velocity_commits_per_week=1,
        timeline=[
            TimelineFrame(
                t_index=0,
                months_ahead=0,
                label="now",
                cells=[NodeMetrics(node_id="now", kind="module", label="now.py", path="now.py", mass=1, velocity=1, momentum=1, pressure=0.1)],
                narrative="now",
            ),
            TimelineFrame(
                t_index=1,
                months_ahead=8,
                label="+8mo",
                cells=[
                    NodeMetrics(node_id="hot", kind="module", label="hot.py", path="hot.py", mass=1, velocity=1, momentum=1, pressure=1.8),
                    NodeMetrics(node_id="next", kind="module", label="next.py", path="next.py", mass=1, velocity=1, momentum=1, pressure=1.2),
                ],
                narrative="core is hot",
            ),
        ],
        heuristic=True,
    )
    reading = forecast_reading(bundle)
    assert reading["state"] == "forecast"
    assert reading["repo"] == "Aether"
    assert reading["frame"] == "+8mo"
    assert reading["path"] == "hot.py"
    assert reading["band"] == "high-pressure"
    assert reading["pressure"] == 1.8
    assert reading["neighbors"][0]["path"] == "next.py"
    assert "hot.py" in headline(reading)
    assert "P 1.80" in headline(reading)


def test_live_route_follows_repo_and_hides_pressure_while_ingesting(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "model_path", None)
    db = AetherDB(tmp_path / "aether.db")
    db.upsert_universe(
        Universe(
            id="u1",
            repo_path="/work/Aether",
            snapshots=[_snap("a", "2025-01-01T00:00:00+00:00"), _snap("b", "2026-01-01T00:00:00+00:00")],
            velocity_commits_per_week=2,
        )
    )
    db.conn.close()

    with TestClient(api_mod.app) as client:
        missing = client.get("/v1/live", params={"repo": "/work/other"})
        assert missing.status_code == 200
        assert missing.json()["state"] == "missing"
        assert missing.json()["pressure"] is None

        ready = client.get("/v1/live", params={"repo": "/work/Aether"})
        assert ready.status_code == 200
        body = ready.json()
        assert body["state"] == "forecast"
        assert body["repo"] == "Aether"
        assert body["frame"]
        assert isinstance(body["pressure"], float)

        queued = client.post("/v1/jobs", json={"path": "/work/pandas"})
        assert queued.status_code == 200
        ingesting = client.get("/v1/live", params={"repo": "/work/pandas"})
        assert ingesting.status_code == 200
        assert ingesting.json()["state"] == "ingesting"
        assert ingesting.json()["pressure"] is None
        assert "P " not in headline(ingesting.json())

        still = client.get("/v1/live", params={"repo": "/work/Aether"})
        assert still.json()["state"] == "forecast"
