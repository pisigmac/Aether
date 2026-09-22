import sys
from pathlib import Path

from aether.acquisition.git_ingest import IngestRequest
from aether.pipeline import build_universe
from aether.storage.db import AetherDB

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "polyglot-debt"


def test_ingest_fixture(tmp_path: Path):
    sys.path.insert(0, str(FIXTURE))
    import seed_git

    seed_git.main()
    db = AetherDB(tmp_path / "aether.db")
    marks: list[tuple[int, str]] = []
    universe, _warnings = build_universe(
        IngestRequest(path=str(FIXTURE)),
        db,
        on_progress=lambda pct, stage: marks.append((pct, stage)),
    )
    assert marks
    assert marks[-1][0] == 100
    assert any("Parsing snapshot" in stage for _pct, stage in marks)
    assert universe.snapshots
    assert universe.license == "MIT"
    forecast = db.get_forecast(universe.id)
    assert forecast is not None
    assert forecast.ghosts
    assert any(frame.months_ahead == 8 for frame in forecast.timeline)
    assert any("heuristic" in w.lower() for w in forecast.warnings)
