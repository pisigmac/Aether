from __future__ import annotations

import hashlib


def stable_id(*parts: str) -> str:
    raw = "::".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def snapshot_hash(commit_sha: str, node_ids: list[str], edge_keys: list[str]) -> str:
    payload = commit_sha + "|" + ",".join(sorted(node_ids)) + "|" + ",".join(sorted(edge_keys))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def module_id(path: str) -> str:
    return stable_id("module", path)


def symbol_id(path: str, name: str) -> str:
    return stable_id("symbol", path, name)


def contract_id(kind: str, name: str) -> str:
    return stable_id("contract", kind, name)


def schema_id(table: str) -> str:
    return stable_id("schema", table)


def service_id(name: str) -> str:
    return stable_id("service", name)
