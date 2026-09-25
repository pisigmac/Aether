from __future__ import annotations

import json
from pathlib import Path

from aether.ir.models import Contract, Edge, EdgeKind, Node, NodeKind
from aether.parsers.ids import contract_id, module_id, service_id

# Name-matching stays at 2.5. An OpenAPI hit is the butterfly weight cap.
NAME_HTTP_WEIGHT = 2.5
NAME_SERVICE_WEIGHT = 1.0
OPENAPI_HTTP_WEIGHT = 3.0
OPENAPI_SERVICE_WEIGHT = 1.5


def link_contracts(
    nodes: list[Node],
    edges: list[Edge],
    contracts: list[Contract],
    openapi_doc: dict | None = None,
) -> tuple[list[Node], list[Edge], list[Contract]]:
    """Bind frontend fetch URLs to OpenAPI when a spec exists, else to backend routes by name."""
    http = [c for c in contracts if c.kind == "http"]
    openapi_paths = _ingest_openapi(nodes, contracts, openapi_doc)

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
        spec_path = _match_openapi(tc.name, openapi_paths)
        if spec_path is not None:
            cid = contract_id("http", spec_path)
            edges.append(Edge(src=tid, dst=cid, kind=EdgeKind.HTTP, weight=OPENAPI_HTTP_WEIGHT))
            edges.append(Edge(src=frontend, dst=cid, kind=EdgeKind.HTTP, weight=OPENAPI_SERVICE_WEIGHT))
            matched.add(tid)
            matched.add(cid)
            continue
        key = _norm(tc.name)
        peers = [c for c in python_http.values() if _norm(c.name) == key]
        if peers:
            for pc in peers:
                edges.append(Edge(src=tid, dst=pc.id, kind=EdgeKind.HTTP, weight=NAME_HTTP_WEIGHT))
                edges.append(Edge(src=frontend, dst=pc.id, kind=EdgeKind.HTTP, weight=NAME_SERVICE_WEIGHT))
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
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _ingest_openapi(
    nodes: list[Node],
    contracts: list[Contract],
    openapi_doc: dict | None,
) -> list[str]:
    if not openapi_doc:
        return []
    paths: list[str] = []
    known = {c.id for c in contracts}
    node_ids = {n.id for n in nodes}
    for path in (openapi_doc.get("paths") or {}):
        if not isinstance(path, str) or not path.startswith("/"):
            continue
        paths.append(path)
        cid = contract_id("http", path)
        if cid not in known:
            contracts.append(Contract(id=cid, kind="http", name=path, detail="openapi"))
            known.add(cid)
        if cid not in node_ids:
            nodes.append(
                Node(id=cid, kind=NodeKind.CONTRACT, export_name=path, extra={"source": "openapi"})
            )
            node_ids.add(cid)
        else:
            for node in nodes:
                if node.id == cid:
                    node.extra["openapi"] = True
                    break
    return paths


def _match_openapi(fetch: str, paths: list[str]) -> str | None:
    if not paths:
        return None
    key = _norm(fetch)
    exact = sorted(path for path in paths if _norm(path) == key)
    if exact:
        return exact[0]
    fetch_segs = [seg for seg in key.split("/") if seg]
    ranked: list[tuple[int, str]] = []
    for path in paths:
        spec_segs = [seg for seg in _norm(path).split("/") if seg]
        if len(spec_segs) != len(fetch_segs):
            continue
        params = 0
        ok = True
        for got, spec in zip(fetch_segs, spec_segs):
            if _is_param(spec):
                params += 1
            elif got != spec:
                ok = False
                break
        if ok and params:
            ranked.append((params, path))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][1]


def _is_param(segment: str) -> bool:
    return segment.startswith("{") and segment.endswith("}") and len(segment) > 2


def _norm(path: str) -> str:
    p = path.strip()
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/") or "/"


def module_for_path(path: str) -> str:
    return module_id(path)
