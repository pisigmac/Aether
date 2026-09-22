from aether.ir.models import Contract, Edge, EdgeKind, Node, NodeKind, Snapshot
from aether.physics.cost import build_costs
from aether.physics.forecast import build_forecast
from aether.physics.ghosts import run_ghost_lab
from aether.physics.metrics import detect_patterns, node_metrics
from aether.physics.time_machine import build_timeline
from aether.ir.models import Universe


def _snap(sha: str, when: str) -> Snapshot:
    schema = Node(id="sch", kind=NodeKind.SCHEMA, lang="python", path="backend/models.py", export_name="orders", loc=20)
    route_py = Node(id="cpy", kind=NodeKind.CONTRACT, lang="python", path="backend/app.py", export_name="/orders", loc=10)
    route_ts = Node(id="cts", kind=NodeKind.CONTRACT, lang="typescript", path="frontend/lib/api.ts", export_name="/orders", loc=8)
    mod = Node(id="mod", kind=NodeKind.MODULE, lang="python", path="backend/app.py", export_name="backend/app.py", loc=80, complexity=12)
    fe = Node(id="fe", kind=NodeKind.MODULE, lang="typescript", path="frontend/lib/api.ts", export_name="frontend/lib/api.ts", loc=40, complexity=6)
    return Snapshot(
        commit_sha=sha,
        authored_at=when,
        snapshot_hash=sha,
        nodes=[schema, route_py, route_ts, mod, fe],
        edges=[
            Edge(src="mod", dst="sch", kind=EdgeKind.SQL, weight=2),
            Edge(src="mod", dst="cpy", kind=EdgeKind.HTTP, weight=1.5),
            Edge(src="fe", dst="cts", kind=EdgeKind.HTTP, weight=1.5),
            Edge(src="cts", dst="cpy", kind=EdgeKind.HTTP, weight=2.5),
        ],
        contracts=[
            Contract(id="cpy", kind="http", name="/orders", lang="python"),
            Contract(id="cts", kind="http", name="/orders", lang="typescript"),
        ],
    )


def test_patterns_and_metrics():
    snap = _snap("a", "2025-01-01T00:00:00+00:00")
    labels = detect_patterns(snap)
    assert "unbounded_list" in labels
    assert "schema_leak" in labels
    cells = node_metrics(snap)
    assert cells
    assert all(c.mass >= 0 for c in cells)


def test_time_machine_and_ghosts_and_cost():
    snaps = [
        _snap("a", "2024-01-01T00:00:00+00:00"),
        _snap("b", "2025-01-01T00:00:00+00:00"),
    ]
    frames = build_timeline(snaps, 24, velocity=2.0)
    assert frames[0].label == "now"
    assert any(f.months_ahead == 8 for f in frames)
    ghosts = run_ghost_lab(snaps[-1])
    intents = {g.intent for g in ghosts}
    assert "add_pagination" in intents
    assert all("attach via" in g.note.lower() for g in ghosts)
    costs = build_costs(snaps[-1], 24, 2.0)
    assert costs[0].month == 0
    assert costs[-1].egress >= costs[0].egress


def test_forecast_bundle():
    snaps = [_snap("a", "2025-01-01T00:00:00+00:00")]
    universe = Universe(id="u", repo_path="/tmp/x", snapshots=snaps, velocity_commits_per_week=2)
    bundle = build_forecast(universe, horizon_months=24)
    assert bundle.heuristic is True
    assert bundle.butterflies
    assert any(b.months == 8 for b in bundle.butterflies)
    assert "not trained on millions" in bundle.warnings[0].lower()
