import math
import time

from aether.ir.models import Edge, EdgeKind, Node, NodeKind, Snapshot
from aether.physics.butterfly import DIFFUSION_BUDGET_MS, propagate


def _chain() -> Snapshot:
    nodes = [
        Node(id=str(i), kind=NodeKind.MODULE, lang="python", export_name=f"n{i}", path=f"n{i}.py")
        for i in range(4)
    ]
    edges = [
        Edge(src=str(i), dst=str(i + 1), kind=EdgeKind.IMPORT, weight=1.0) for i in range(3)
    ]
    edges.append(Edge(src="0", dst="0", kind=EdgeKind.UNRESOLVED, weight=0.4))
    return Snapshot(
        commit_sha="c",
        authored_at="2026-01-01T00:00:00+00:00",
        snapshot_hash="c",
        nodes=nodes,
        edges=edges,
    )


def _sparse(count: int) -> Snapshot:
    nodes = [
        Node(id=str(i), kind=NodeKind.MODULE, lang="python", export_name=f"m{i}", path=f"m{i}.py")
        for i in range(count)
    ]
    edges: list[Edge] = []
    for i in range(count):
        for step in range(1, 4):
            dst = (i + step * 997) % count
            if dst == i:
                continue
            edges.append(Edge(src=str(i), dst=str(dst), kind=EdgeKind.IMPORT, weight=1.0))
    return Snapshot(
        commit_sha="b",
        authored_at="2026-01-01T00:00:00+00:00",
        snapshot_hash="b",
        nodes=nodes,
        edges=edges,
    )


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    rank = math.ceil(0.95 * len(ordered)) - 1
    return ordered[max(0, rank)]


def test_diffusion_decays_and_ignores_unresolved_self_edges():
    frame = propagate(_chain(), ["0"], 0.0)
    by_id = {item.node_id: item.intensity for item in frame.impacted}
    assert by_id["0"] == 1.0
    assert by_id["1"] == 0.5
    assert by_id["2"] == 0.18
    assert "3" not in by_id
    assert frame.impacted[0].path_type == "origin"


def test_diffusion_p95_meets_the_published_budget():
    runs = 21
    for count, limit in DIFFUSION_BUDGET_MS.items():
        snapshot = _sparse(count)
        propagate(snapshot, ["0"], 8.0)
        samples = []
        for _ in range(runs):
            started = time.perf_counter()
            frame = propagate(snapshot, ["0"], 8.0)
            samples.append((time.perf_counter() - started) * 1000)
        assert frame.impacted
        assert len(frame.impacted) <= 40
        measured = _p95(samples)
        assert measured <= limit, f"{count} nodes p95 {measured:.1f} ms exceeded {limit} ms"
