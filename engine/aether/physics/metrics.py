from __future__ import annotations

from collections import defaultdict

import networkx as nx

from aether.ir.models import (
    EdgeKind,
    EvolutionRecord,
    MetricVector,
    NodeKind,
    NodeMetrics,
    Snapshot,
)


def snapshot_graph(snapshot: Snapshot) -> nx.DiGraph:
    g = nx.DiGraph()
    for n in snapshot.nodes:
        g.add_node(n.id, **n.model_dump())
    for e in snapshot.edges:
        if e.src == e.dst and e.kind == EdgeKind.UNRESOLVED:
            g.add_node(e.src)
            continue
        if e.src not in g:
            g.add_node(e.src)
        if e.dst not in g:
            g.add_node(e.dst)
        g.add_edge(e.src, e.dst, kind=e.kind.value, weight=e.weight)
    return g


def _cycles(g: nx.DiGraph) -> tuple[set[str], int]:
    """SCC-based cycles — simple_cycles is exponential on real library graphs."""
    nodes: set[str] = set()
    count = 0
    for comp in nx.strongly_connected_components(g):
        if len(comp) > 1:
            nodes.update(comp)
            count += 1
            continue
        node = next(iter(comp))
        if g.has_edge(node, node):
            nodes.add(node)
            count += 1
    return nodes, count


def node_metrics(snapshot: Snapshot, churn: dict[str, float] | None = None) -> list[NodeMetrics]:
    g = snapshot_graph(snapshot)
    churn = churn or {}
    cycle_nodes, _ = _cycles(g)
    labels = detect_patterns(snapshot)

    dependents: dict[str, int] = defaultdict(int)
    for _u, v in g.edges():
        dependents[v] += 1

    out: list[NodeMetrics] = []
    for n in snapshot.nodes:
        if n.kind not in {NodeKind.MODULE, NodeKind.SERVICE, NodeKind.SCHEMA, NodeKind.CONTRACT}:
            continue
        dep = dependents.get(n.id, 0)
        mass = (n.loc / 50.0) + (n.complexity / 10.0) + dep
        if n.kind == NodeKind.SCHEMA:
            mass += 2.0
        if n.kind == NodeKind.CONTRACT:
            mass += 1.2
        velocity = churn.get(n.path or n.id, churn.get(n.id, 0.15))
        pressure = 0.0
        pressure += 0.4 if n.id in cycle_nodes else 0.0
        pressure += min(n.complexity / 25.0, 1.2)
        if n.kind == NodeKind.MODULE and n.loc > 200:
            pressure += 0.6
        if n.kind == NodeKind.SCHEMA:
            pressure += 0.85
        if n.kind == NodeKind.CONTRACT and "unbounded_list" in labels and n.export_name.rstrip("/").endswith("s"):
            pressure += 0.7
        out.append(
            NodeMetrics(
                node_id=n.id,
                kind=n.kind.value,
                label=n.export_name or n.path or n.id,
                path=n.path,
                lang=n.lang,
                mass=round(mass, 3),
                velocity=round(velocity, 3),
                momentum=round(mass * velocity, 3),
                pressure=round(min(pressure, 3.0), 3),
                dependents=dep,
            )
        )
    return out


def detect_patterns(snapshot: Snapshot) -> list[str]:
    labels: set[str] = set()
    g = snapshot_graph(snapshot)
    cycle_nodes, _ = _cycles(g)
    if cycle_nodes:
        labels.add("cyclic_dep")

    for n in snapshot.nodes:
        if n.kind == NodeKind.MODULE and (n.loc > 250 or n.complexity > 40):
            labels.add("god_module")
        extra = n.extra or {}
        if n.kind == NodeKind.SCHEMA and extra.get("missing_index"):
            labels.add("missing_index")

    http_by_name: dict[str, list[str]] = defaultdict(list)
    for n in snapshot.nodes:
        if n.kind == NodeKind.CONTRACT:
            http_by_name[n.export_name].append(n.lang)

    for name, langs in http_by_name.items():
        if "python" in langs and "typescript" in langs:
            # frontend bound to a collection route with no page/limit hint
            if name.rstrip("/").endswith("s") and "page" not in name:
                labels.add("unbounded_list")

    sql_edges = [e for e in snapshot.edges if e.kind == EdgeKind.SQL]
    http_edges = [e for e in snapshot.edges if e.kind == EdgeKind.HTTP]
    if sql_edges and http_edges:
        labels.add("schema_leak")

    if len(http_edges) >= 6:
        labels.add("chatty_rpc")

    return sorted(labels)


def metric_vector(snapshot: Snapshot, cells: list[NodeMetrics] | None = None) -> MetricVector:
    cells = cells or node_metrics(snapshot)
    labels = detect_patterns(snapshot)
    g = snapshot_graph(snapshot)
    _, cycle_count = _cycles(g)
    god = sum(1 for n in snapshot.nodes if n.kind == NodeKind.MODULE and n.loc > 250)
    return MetricVector(
        mass=round(sum(c.mass for c in cells), 3),
        coupling=round(sum(c.dependents for c in cells) / max(len(cells), 1), 3),
        churn=round(sum(c.velocity for c in cells) / max(len(cells), 1), 3),
        cycles=cycle_count,
        god_module_count=god,
        contract_leak_count=int("schema_leak" in labels) + int("unbounded_list" in labels),
    )


def evolution_record(
    repo_id: str,
    snapshot: Snapshot,
    prev: Snapshot | None,
    next_target: MetricVector | None = None,
) -> EvolutionRecord:
    cells = node_metrics(snapshot)
    vec = metric_vector(snapshot, cells)
    delta = {"nodes_added": 0, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0}
    if prev:
        prev_n = {n.id for n in prev.nodes}
        cur_n = {n.id for n in snapshot.nodes}
        prev_e = {(e.src, e.dst, e.kind) for e in prev.edges}
        cur_e = {(e.src, e.dst, e.kind) for e in snapshot.edges}
        delta = {
            "nodes_added": len(cur_n - prev_n),
            "nodes_removed": len(prev_n - cur_n),
            "edges_added": len(cur_e - prev_e),
            "edges_removed": len(prev_e - cur_e),
        }
    return EvolutionRecord(
        repo_id=repo_id,
        commit_sha=snapshot.commit_sha,
        authored_at=snapshot.authored_at,
        snapshot_hash=snapshot.snapshot_hash,
        metric_vector=vec,
        pattern_labels=detect_patterns(snapshot),
        delta_from_prev=delta,
        horizon_target=next_target,
    )


def path_churn(snapshots: list[Snapshot]) -> dict[str, float]:
    touches: dict[str, int] = defaultdict(int)
    for snap in snapshots:
        seen: set[str] = set()
        for n in snap.nodes:
            key = n.path or n.id
            if key in seen:
                continue
            seen.add(key)
            touches[key] += 1
    window = max(len(snapshots), 1)
    return {k: v / window for k, v in touches.items()}
