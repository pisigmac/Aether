from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aether.acquisition.adapters import SoftwareHeritageAdapter
from aether.acquisition.git_ingest import IngestRequest
from aether.jobs import ProgressFn
from aether.pipeline import build_universe
from aether.storage.db import AetherDB

DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "datasets" / "corpus" / "manifest.json"


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_MANIFEST
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("repos"):
        raise ValueError(f"Corpus manifest has no repos: {target}")
    return data


def parse_local_overrides(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Local override must be NAME=PATH, got {item!r}")
        name, path = item.split("=", 1)
        out[name.strip()] = path.strip()
    return out


def seed_corpus(
    db: AetherDB,
    manifest_path: Path | None = None,
    *,
    lookback_months: int = 36,
    max_samples: int = 12,
    local_overrides: dict[str, str] | None = None,
    data_dir: Path | None = None,
    fetch_swhids: bool = False,
    swh_adapter: SoftwareHeritageAdapter | None = None,
    on_progress: ProgressFn | None = None,
) -> list[dict[str, Any]]:
    """Ingest each license-filtered seed repo. Existing universes are upserted, not wiped."""
    manifest = load_manifest(manifest_path)
    overrides = local_overrides or {}
    report = on_progress or (lambda _pct, _stage: None)
    results: list[dict[str, Any]] = []
    repos = list(manifest["repos"])
    for i, repo in enumerate(repos):
        name = str(repo.get("name") or f"repo-{i}")
        report(int((i / max(len(repos), 1)) * 90), f"Seeding {name}")
        local = overrides.get(name) or str(repo.get("path") or "")
        req = IngestRequest(
            path=local,
            url="" if local else str(repo.get("url") or ""),
            lookback_months=lookback_months,
            max_samples=max_samples,
        )
        row: dict[str, Any] = {
            "name": name,
            "url": repo.get("url") or "",
            "spdx": repo.get("spdx") or "",
            "ok": False,
        }
        try:
            universe, warnings = build_universe(req, db, data_dir=data_dir)
            records = db.list_evolution(universe.id)
            labeled = [r for r in records if r.horizon_target is not None]
            swhids = list(repo.get("swhids") or [])
            if fetch_swhids:
                swhids = _fill_swhids(repo, swh_adapter)
            row.update(
                {
                    "ok": True,
                    "universe_id": universe.id,
                    "license": universe.license,
                    "snapshots": len(universe.snapshots),
                    "evolution_records": len(records),
                    "horizon_target_records": len(labeled),
                    "warnings": warnings,
                    "swhids": swhids,
                }
            )
        except Exception as exc:
            row["error"] = str(exc)
        results.append(row)
    report(100, "Seed corpus ready")
    return results


def _fill_swhids(repo: dict[str, Any], adapter: SoftwareHeritageAdapter | None) -> list[str]:
    origin = str(repo.get("swh_origin") or repo.get("url") or "")
    if not origin:
        return list(repo.get("swhids") or [])
    try:
        rows = (adapter or SoftwareHeritageAdapter()).fetch_history(origin)
    except Exception:
        return list(repo.get("swhids") or [])
    ids: list[str] = []
    for item in rows:
        for key in ("revision", "directory", "snapshot"):
            value = item.get(key)
            if value and value not in ids:
                ids.append(str(value))
    return ids
