from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from aether.acquisition.sampler import (
    SampleCommit,
    batch_show_files,
    diff_paths,
    list_source_paths,
    show_file,
)
from aether.ir.models import Contract, Edge, EdgeKind, Node, Snapshot
from aether.parsers.contracts import link_contracts, load_openapi
from aether.parsers.ids import snapshot_hash
from aether.parsers.python_parser import PyExtract, parse_python
from aether.parsers.typescript_parser import TsExtract, parse_typescript

PY_EXT = {".py"}
TS_EXT = {".ts", ".tsx", ".js", ".jsx"}
SKIP_PARTS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".git",
    "data",
    "tests",
    "test",
    ".aether",
    "docs",
    "doc",
    "benchmarks",
    "asv_bench",
    "ci",
    ".github",
    "vendor",
    "examples",
    "site-packages",
    "_testing",
    "scripts",
}


@dataclass
class ParsedGraph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)


def parse_snapshot(root: Path, sample: SampleCommit) -> Snapshot:
    sha = None if sample.sha == "WORKING_TREE" else sample.sha
    paths = _wanted_paths(list_source_paths(root, sha))
    extracts = _parse_paths(root, sha, paths)
    return _assemble(root, sample, extracts)


def parse_history(
    root: Path,
    samples: list[SampleCommit],
    on_snapshot: Callable[[int, str], None] | None = None,
) -> list[Snapshot]:
    """Parse a commit series, re-reading only files that changed since the previous sample."""
    cached: dict[str, PyExtract | TsExtract] = {}
    snapshots: list[Snapshot] = []
    prev_sha: str | None = None
    for index, sample in enumerate(samples):
        if on_snapshot:
            on_snapshot(index, sample.sha)
        sha = None if sample.sha == "WORKING_TREE" else sample.sha
        if prev_sha and sha and prev_sha != sha:
            touched, removed = diff_paths(root, prev_sha, sha)
            for path in removed:
                cached.pop(path, None)
            to_read = _wanted_paths(touched)
            for path in touched:
                if path not in to_read:
                    cached.pop(path, None)
        else:
            to_read = _wanted_paths(list_source_paths(root, sha))
            keep = set(to_read)
            for path in list(cached):
                if path not in keep:
                    cached.pop(path, None)
        parsed = _parse_paths(root, sha, to_read)
        for path in to_read:
            extract = parsed.get(path)
            if extract is None:
                cached.pop(path, None)
            else:
                cached[path] = extract
        snapshots.append(_assemble(root, sample, cached))
        prev_sha = sha
    return snapshots


def _wanted_paths(paths: list[str]) -> list[str]:
    return [p for p in paths if Path(p).suffix in PY_EXT | TS_EXT and not _skip(p)]


def _parse_paths(root: Path, sha: str | None, paths: list[str]) -> dict[str, PyExtract | TsExtract]:
    found: dict[str, PyExtract | TsExtract] = {}
    sources = batch_show_files(root, sha, paths)
    for rel in paths:
        source = sources.get(rel, "")
        if not source.strip():
            continue
        if Path(rel).suffix in PY_EXT:
            found[rel] = parse_python(rel, source)
        else:
            found[rel] = parse_typescript(rel, source)
    return found


def _assemble(root: Path, sample: SampleCommit, extracts: dict[str, PyExtract | TsExtract]) -> Snapshot:
    sha = None if sample.sha == "WORKING_TREE" else sample.sha
    nodes: list[Node] = []
    edges: list[Edge] = []
    contracts: list[Contract] = []
    import_index: dict[str, str] = {}
    ordered = [extracts[path] for path in sorted(extracts)]

    for extract in ordered:
        nodes.extend(extract.nodes)
        edges.extend(extract.edges)
        contracts.extend(extract.contracts)
        for n in extract.nodes:
            if n.kind.value == "module":
                import_index[_module_key(n.path)] = n.id

    for extract in ordered:
        module = next((n for n in extract.nodes if n.kind.value == "module"), None)
        if module is None:
            continue
        python = module.lang == "python"
        for spec in extract.imports:
            dst = _resolve_import(module.path, spec, import_index, python)
            if dst:
                edges.append(Edge(src=module.id, dst=dst, kind=EdgeKind.IMPORT, weight=1.0))
            else:
                edges.append(Edge(src=module.id, dst=module.id, kind=EdgeKind.UNRESOLVED, weight=0.15))

    openapi = load_openapi(root, show_file, sha)
    nodes, edges, contracts = link_contracts(nodes, edges, contracts, openapi)
    node_ids = [n.id for n in nodes]
    edge_keys = [f"{e.src}>{e.dst}:{e.kind}" for e in edges]
    return Snapshot(
        commit_sha=sample.sha,
        authored_at=sample.authored_at,
        snapshot_hash=snapshot_hash(sample.sha, node_ids, edge_keys),
        nodes=_dedupe_nodes(nodes),
        edges=_dedupe_edges(edges),
        contracts=_dedupe_contracts(contracts),
    )


def _skip(path: str) -> bool:
    parts = Path(path).parts
    if any(p in SKIP_PARTS for p in parts):
        return True
    name = Path(path).name
    return (
        name.endswith(".d.ts")
        or name.endswith(".test.ts")
        or name.startswith("test_")
        or name == "seed_git.py"
    )


def _module_key(path: str) -> str:
    p = path.replace("\\", "/")
    if p.endswith(".py"):
        return p[:-3].replace("/", ".")
    for ext in (".tsx", ".ts", ".jsx", ".js"):
        if p.endswith(ext):
            return p[: -len(ext)]
    return p


def _resolve_import(src_path: str, spec: str, index: dict[str, str], python: bool) -> str | None:
    if python:
        if spec in index:
            return index[spec]
        for key, nid in index.items():
            if key.endswith(spec) or spec.endswith(key.split(".")[-1]):
                return nid
        return None
    if spec.startswith("."):
        cleaned = spec
        while cleaned.startswith("./"):
            cleaned = cleaned[2:]
        parent = str(Path(src_path).parent).replace("\\", "/")
        if parent == ".":
            guess = cleaned
        else:
            guess = f"{parent}/{cleaned}"
        return index.get(guess)
    return None


def _dedupe_nodes(nodes: list[Node]) -> list[Node]:
    seen: dict[str, Node] = {}
    for n in nodes:
        seen[n.id] = n
    return list(seen.values())


def _dedupe_edges(edges: list[Edge]) -> list[Edge]:
    seen: set[tuple] = set()
    out: list[Edge] = []
    for e in edges:
        key = (e.src, e.dst, e.kind)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def _dedupe_contracts(contracts: list[Contract]) -> list[Contract]:
    seen: dict[str, Contract] = {}
    for c in contracts:
        seen[c.id] = c
    return list(seen.values())
