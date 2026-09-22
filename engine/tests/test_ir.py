from aether.ir.models import ForecastBundle, Node, NodeKind, Snapshot


def test_ir_version_and_forecast_shape():
    node = Node(id="n1", kind=NodeKind.MODULE, path="a.py", export_name="a")
    snap = Snapshot(commit_sha="abc", authored_at="2026-01-01T00:00:00+00:00", snapshot_hash="h", nodes=[node])
    assert snap.nodes[0].kind == NodeKind.MODULE
    bundle = ForecastBundle(universe_id="u", repo_path="/tmp/x", heuristic=True)
    dumped = bundle.model_dump()
    assert dumped["ir_version"] == 1
    assert dumped["heuristic"] is True
    assert "timeline" in dumped and "ghosts" in dumped and "costs" in dumped
