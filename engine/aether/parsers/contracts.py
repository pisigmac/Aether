from __future__ import annotations

import json
from pathlib import Path

from aether.ir.models import Contract, Edge, EdgeKind, Node, NodeKind
from aether.parsers.ids import contract_id, module_id, service_id


def link_contracts(
    nodes: list[Node],
    edges: list[Edge],
    contracts: list[Contract],
    openapi_doc: dict | None = None,
) -> tuple[list[Node], list[Edge], list[Contract]]:
    """Bind frontend fetch URLs to backend routes. Unmatched stay unresolved."""
    http = [c for c in contracts if c.kind == "http"]
    by_name: dict[str, list[Contract]] = {}
    for c in http:
        by_name.setdefault(_norm(c.name), []).append(c)

    if openapi_doc:
        for path, methods in (openapi_doc.get("paths") or {}).items():
            cid = contract_id("http", path)
            if cid not in {c.id for c in contracts}:
                contracts.append(Contract(id=cid, kind="http", name=path, detail="openapi"))
                nodes.append(
                    Node(id=cid, kind=NodeKind.CONTRACT, export_name=path, extra={"source": "openapi"})
                )
            by_name.setdefault(_norm(path), [])

    python_http = {c.id: c for c in http if c.lang == "python"}
    ts_http = {c.id: c for c in http if c.lang == "typescript"}

    backend = service_id("backend")
    frontend = service_id("frontend")
    nodes.append(Node(id=backend, kind=NodeKind.SERVICE, export_name="backend", lang="python"))
    nodes.append(Node(id=frontend, kind=NodeKind.SERVICE, export_name="frontend", lang="typescript"))

    for n in nodes:
        if n.kind == NodeKind.MODULE and n.lang == "python":
            edges.append(Edge(src=backend, dst=n.id, kind=EdgeKind.IMPORT, weight=0.1))
        if n.kind == NodeKind.MODULE and n.lang == "typescript":
            edges.append(Edge(src=frontend, dst=n.id, kind=EdgeKind.IMPORT, weight=0.1))

    matched: set[str] = set()
    for tid, tc in ts_http.items():
        key = _norm(tc.name)
        peers = [c for c in python_http.values() if _norm(c.name) == key]
        if peers:
            for pc in peers:
                edges.append(Edge(src=tid, dst=pc.id, kind=EdgeKind.HTTP, weight=2.5))
                edges.append(Edge(src=frontend, dst=pc.id, kind=EdgeKind.HTTP, weight=1.0))
                matched.add(tid)
                matched.add(pc.id)
        else:
            edges.append(Edge(src=tid, dst=tid, kind=EdgeKind.UNRESOLVED, weight=0.4))

    # schema → python modules already have sql edges; lift to backend service
    for n in nodes:
        if n.kind == NodeKind.SCHEMA:
            edges.append(Edge(src=backend, dst=n.id, kind=EdgeKind.SQL, weight=1.0))

    return nodes, edges, contracts


def load_openapi(root: Path, show_file, sha: str | None) -> dict | None:
    for candidate in ("openapi.json", "backend/openapi.json", "docs/openapi.json"):
        raw = show_file(root, candidate, sha)
        if not raw:
            continue
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    return None


def _norm(path: str) -> str:
    p = path.strip()
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/") or "/"


def module_for_path(path: str) -> str:
    return module_id(path)
