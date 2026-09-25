from __future__ import annotations

from collections import defaultdict, deque

from aether.ir.models import ButterflyFrame, ChangeSet, EdgeKind, ImpactedNode, NodeKind, Snapshot

# One Butterfly horizon, sparse graph (3 outgoing edges per node).
# NetworkX graph build missed both bars (about 300 ms at 10k, 1.2 s at 50k).
DIFFUSION_BUDGET_MS = {10_000: 250, 50_000: 800}


def apply_changeset(snapshot: Snapshot, changeset: ChangeSet | None) -> Snapshot:
    if not changeset:
        return snapshot
    nodes = {n.id: n.model_copy() for n in snapshot.nodes}
    edges = list(snapshot.edges)
    for mut in changeset.mutations:
        if mut.op == "add" and mut.node:
            nodes[mut.node.id] = mut.node
        if mut.op == "add" and mut.edge:
            edges.append(mut.edge)
        if mut.op == "remove" and mut.node:
            nodes.pop(mut.node.id, None)
        if mut.op == "remove" and mut.edge:
            edges = [
                e
                for e in edges
                if not (e.src == mut.edge.src and e.dst == mut.edge.dst and e.kind == mut.edge.kind)
            ]
        if mut.op == "retarget" and mut.retarget_src and mut.retarget_dst:
            edges = [
                e.model_copy(update={"dst": mut.retarget_dst}) if e.src == mut.retarget_src else e
                for e in edges
            ]
    contracts = list(snapshot.contracts)
    return snapshot.model_copy(update={"nodes": list(nodes.values()), "edges": edges, "contracts": contracts})


def origins_from_changeset(snapshot: Snapshot, changeset: ChangeSet | None) -> list[str]:
    if not changeset:
        schema = [n.id for n in snapshot.nodes if n.kind == NodeKind.SCHEMA]
        return schema[:3]
    ids: list[str] = []
    touched = set(changeset.touched_paths)
    for n in snapshot.nodes:
        if n.path in touched or n.id in touched:
            ids.append(n.id)
    for mut in changeset.mutations:
        if mut.node:
            ids.append(mut.node.id)
    return list(dict.fromkeys(ids)) or [n.id for n in snapshot.nodes if n.kind == NodeKind.SCHEMA][:1]


def propagate(snapshot: Snapshot, origins: list[str], months: float) -> ButterflyFrame:
    outs, meta = _adjacency(snapshot)
    intensity: dict[str, float] = defaultdict(float)
    path_type: dict[str, str] = {}
    for origin in origins:
        if origin not in meta:
            continue
        intensity[origin] = max(intensity[origin], 1.0)
        path_type[origin] = "origin"
        queue = deque([(origin, 0, 1.0)])
        seen = {origin}
        while queue:
            node, depth, seed = queue.popleft()
            for dst, kind, weight in outs.get(node, ()):
                if dst in seen:
                    continue
                decay = 0.72 ** depth
                time_boost = 1.0 + months / 24.0
                nxt = seed * decay * min(weight, 3.0) / 2.0 * time_boost
                if nxt < 0.08:
                    continue
                seen.add(dst)
                intensity[dst] = max(intensity[dst], nxt)
                path_type[dst] = _path_type(kind, meta.get(dst, {}))
                queue.append((dst, depth + 1, nxt))

    labels = {n.id: (n.export_name or n.path or n.id) for n in snapshot.nodes}
    kinds = {n.id: n.kind.value for n in snapshot.nodes}
    impacted = [
        ImpactedNode(
            node_id=nid,
            label=labels.get(nid, nid),
            kind=kinds.get(nid, "unknown"),
            intensity=round(val, 3),
            path_type=path_type.get(nid, ""),
        )
        for nid, val in intensity.items()
    ]
    impacted.sort(key=lambda x: x.intensity, reverse=True)
    return ButterflyFrame(months=months, origin_ids=origins, impacted=impacted[:40])


def _adjacency(snapshot: Snapshot) -> tuple[dict[str, list[tuple[str, str, float]]], dict[str, dict]]:
    outs: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    meta: dict[str, dict] = {
        node.id: {"kind": node.kind.value, "lang": node.lang} for node in snapshot.nodes
    }
    unresolved = EdgeKind.UNRESOLVED
    for edge in snapshot.edges:
        src = edge.src
        dst = edge.dst
        kind = edge.kind
        if src == dst and kind == unresolved:
            if src not in meta:
                meta[src] = {}
            continue
        if src not in meta:
            meta[src] = {}
        if dst not in meta:
            meta[dst] = {}
        outs[src].append((dst, kind.value, edge.weight))
    return outs, meta


def _path_type(edge_kind: str, node_data: dict) -> str:
    kind = node_data.get("kind", "")
    if kind == NodeKind.SCHEMA.value or edge_kind == EdgeKind.SQL.value:
        return "schema"
    if kind == NodeKind.CONTRACT.value or edge_kind == EdgeKind.HTTP.value:
        return "http_contract"
    if node_data.get("lang") == "typescript":
        return "frontend_module"
    if node_data.get("lang") == "python":
        return "backend_module"
    return edge_kind or "graph"
