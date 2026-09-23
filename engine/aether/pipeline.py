from __future__ import annotations

import json
from pathlib import Path

from aether.acquisition.git_ingest import IngestRequest, ingest_repo
from aether.acquisition.sampler import show_file
from aether.ir.models import ChangeSet, Mutation, Node, NodeKind, Universe
from aether.parsers.ids import schema_id, stable_id
from aether.parsers.scan import parse_snapshot
from aether.physics.forecast import build_forecast
from aether.physics.metrics import evolution_record, metric_vector, node_metrics
from aether.jobs import ProgressFn
from aether.storage.db import AetherDB


def build_universe(
    req: IngestRequest,
    db: AetherDB,
    on_progress: ProgressFn | None = None,
    data_dir: Path | None = None,
) -> tuple[Universe, list[str]]:
    report = on_progress or (lambda _pct, _stage: None)
    ingested = ingest_repo(req, data_dir=data_dir, on_progress=report)
    universe_id = stable_id("universe", str(ingested.root))
    snapshots = []
    total = max(len(ingested.samples), 1)
    for i, sample in enumerate(ingested.samples):
        pct = 22 + int((i / total) * 55)
        short = sample.sha[:8] if sample.sha != "WORKING_TREE" else "working tree"
        report(pct, f"Parsing snapshot {i + 1}/{total} ({short})")
        snapshots.append(parse_snapshot(ingested.root, sample))
    universe = Universe(
        id=universe_id,
        repo_path=str(ingested.root),
        license=ingested.license,
        snapshots=snapshots,
        velocity_commits_per_week=ingested.velocity,
    )
    report(78, "Writing universe")
    db.upsert_universe(universe)

    records = []
    for i, snap in enumerate(snapshots):
        report(80 + int((i / max(len(snapshots), 1)) * 6), f"Recording evolution {i + 1}/{len(snapshots)}")
        nxt = None
        if i + 1 < len(snapshots):
            nxt = metric_vector(snapshots[i + 1], node_metrics(snapshots[i + 1]))
        prev = snapshots[i - 1] if i else None
        rec = evolution_record(universe_id, snap, prev, nxt)
        db.upsert_evolution(rec)
        records.append(rec)

    changeset = _maybe_changeset(ingested.root, universe_id, req.pr_ref, snapshots[-1] if snapshots else None)
    report(88, "Saving changeset")
    if changeset:
        db.upsert_changeset(changeset)

    bundle = build_forecast(
        universe,
        extra_warnings=ingested.warnings,
        changeset=changeset,
    )
    report(90, "Running physics forecast")
    db.upsert_forecast(bundle)
    report(100, "Forecast ready")
    return universe, ingested.warnings


def attach_changeset(db: AetherDB, universe_id: str, changeset: ChangeSet) -> ChangeSet:
    universe = db.get_universe(universe_id)
    if not universe:
        raise KeyError(universe_id)
    changeset.universe_id = universe_id
    if not changeset.id:
        changeset.id = stable_id("changeset", universe_id, changeset.label)
    db.upsert_changeset(changeset)
    bundle = build_forecast(universe, changeset=changeset)
    db.upsert_forecast(bundle)
    return changeset


def _maybe_changeset(
    root: Path,
    universe_id: str,
    pr_ref: str,
    latest,
) -> ChangeSet | None:
    planted = root / "planted_pr.json"
    if planted.is_file():
        data = json.loads(planted.read_text(encoding="utf-8"))
        return ChangeSet.model_validate({**data, "universe_id": universe_id})
    if not pr_ref:
        return _infer_schema_delta(root, universe_id, latest)
    raw = show_file(root, pr_ref, None)
    if raw:
        try:
            data = json.loads(raw)
            return ChangeSet.model_validate({**data, "universe_id": universe_id})
        except Exception:
            pass
    return None


def _infer_schema_delta(root: Path, universe_id: str, latest) -> ChangeSet | None:
    """If models mention metadata/status columns, expose them as a schema perturbation."""
    if latest is None:
        return None
    models = show_file(root, "backend/models.py", None)
    if not models or "metadata" not in models:
        return None
    sid = schema_id("orders")
    node = Node(
        id=sid,
        kind=NodeKind.SCHEMA,
        lang="python",
        path="backend/models.py",
        export_name="orders",
        extra={"missing_index": True, "added_columns": ["status", "metadata"]},
    )
    return ChangeSet(
        id=stable_id("changeset", universe_id, "planted-schema"),
        universe_id=universe_id,
        label="planted-schema",
        summary="Add orders.status and orders.metadata (looks harmless today).",
        mutations=[Mutation(op="add", node=node)],
        touched_paths=["backend/models.py"],
    )
