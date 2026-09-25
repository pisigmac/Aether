import os

import pytest

from aether.ir.models import ChangeSet, EvolutionRecord, ForecastBundle, MetricVector, Universe
from aether.storage.db import AetherDB
from tests.test_physics import _snap

pytestmark = pytest.mark.skipif(
    not os.environ.get("AETHER_TEST_DATABASE_URL"),
    reason="Set AETHER_TEST_DATABASE_URL to run the Postgres storage test",
)


def test_postgres_stores_universe_evolution_and_forecast():
    url = os.environ["AETHER_TEST_DATABASE_URL"]
    db = AetherDB(url=url)
    universe_id = "p504-roundtrip"
    try:
        snaps = [_snap("a", "2025-01-01T00:00:00+00:00"), _snap("b", "2026-01-01T00:00:00+00:00")]
        db.upsert_universe(Universe(id=universe_id, repo_path="/tmp/p504", snapshots=snaps, org_id="org-1"))
        db.upsert_evolution(
            EvolutionRecord(
                repo_id=universe_id,
                commit_sha="a",
                authored_at="2025-01-01T00:00:00+00:00",
                snapshot_hash="a",
                metric_vector=MetricVector(mass=1),
            )
        )
        db.upsert_changeset(ChangeSet(id="cs-p504", universe_id=universe_id, label="note"))
        db.upsert_forecast(ForecastBundle(universe_id=universe_id, repo_path="/tmp/p504", heuristic=True))

        again = AetherDB(url=url)
        assert any(row["id"] == universe_id for row in again.list_universes("org-1"))
        assert universe_id not in {row["id"] for row in again.list_universes("org-2")}
        loaded = again.get_universe(universe_id)
        assert loaded is not None
        assert loaded.org_id == "org-1"
        assert len(loaded.snapshots) == 2
        assert again.get_snapshot(universe_id, "b") is not None
        evolution = again.list_evolution(universe_id)
        assert evolution[0].metric_vector.mass == 1
        assert again.list_changesets(universe_id)[0].label == "note"
        forecast = again.get_forecast(universe_id)
        assert forecast is not None
        assert forecast.heuristic is True
        again.delete_universe(universe_id)
        gone = AetherDB(url=url)
        assert gone.get_universe(universe_id) is None
        assert gone.get_forecast(universe_id) is None
        assert gone.list_evolution(universe_id) == []
        again.conn.close()
        gone.conn.close()
    finally:
        db.delete_universe(universe_id)
        db.conn.close()
