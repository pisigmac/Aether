from __future__ import annotations

from pathlib import Path

from aether.config import settings
from aether.ir.models import ChangeSet, ForecastBundle, Snapshot, Universe
from aether.physics.butterfly import apply_changeset, origins_from_changeset, propagate
from aether.physics.cost import build_costs
from aether.physics.ghosts import run_ghost_lab
from aether.physics.metrics import metric_vector, node_metrics
from aether.physics.predictor import Predictor, resolve_predictor
from aether.physics.time_machine import build_timeline


def build_forecast(
    universe: Universe,
    horizon_months: int = 24,
    changeset: ChangeSet | None = None,
    extra_warnings: list[str] | None = None,
    predictor: Predictor | None = None,
    model_path: Path | None = None,
) -> ForecastBundle:
    if not universe.snapshots:
        raise ValueError("Universe has no snapshots to forecast.")
    latest = universe.snapshots[-1]
    projected = apply_changeset(latest, changeset)
    predictor = predictor or resolve_predictor(model_path or settings.model_path)
    learned = predictor.name == "learned"
    cost_labels = _predicted_cost_labels(predictor, universe, projected) if learned else None
    timeline = build_timeline(
        universe.snapshots,
        horizon_months,
        universe.velocity_commits_per_week,
        predictor=predictor,
        pattern_labels=cost_labels,
    )
    origins = origins_from_changeset(projected, changeset)
    butterflies = [propagate(projected, origins, m) for m in (0.0, 3.0, 8.0, 24.0) if m <= horizon_months]
    ghosts = run_ghost_lab(projected)
    costs = build_costs(
        projected,
        horizon_months,
        universe.velocity_commits_per_week,
        labels=cost_labels,
    )
    if learned:
        source = (
            f"Learned model {predictor.model_id} · trained on {predictor.training_records} "
            "Evolution Records — not millions of repositories."
        )
    else:
        source = "Heuristic forecast from this repo's own history — not trained on millions of repositories."
    warnings = [source, *(extra_warnings or [])]
    if changeset:
        warnings.append(f"ChangeSet '{changeset.label}' applied as an IR perturbation.")
    return ForecastBundle(
        universe_id=universe.id,
        repo_path=universe.repo_path,
        horizon_months=horizon_months,
        velocity_commits_per_week=universe.velocity_commits_per_week,
        timeline=timeline,
        butterflies=butterflies,
        ghosts=ghosts,
        costs=costs,
        warnings=warnings,
        heuristic=not learned,
        license=universe.license,
        model_id=predictor.model_id,
        training_records=predictor.training_records,
    )


def _snapshot_delta(prev: Snapshot | None, cur: Snapshot) -> dict[str, int]:
    if prev is None:
        return {"nodes_added": 0, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0}
    prev_n = {n.id for n in prev.nodes}
    cur_n = {n.id for n in cur.nodes}
    prev_e = {(e.src, e.dst, e.kind) for e in prev.edges}
    cur_e = {(e.src, e.dst, e.kind) for e in cur.edges}
    return {
        "nodes_added": len(cur_n - prev_n),
        "nodes_removed": len(prev_n - cur_n),
        "edges_added": len(cur_e - prev_e),
        "edges_removed": len(prev_e - cur_e),
    }


def _predicted_cost_labels(predictor: Predictor, universe: Universe, projected: Snapshot) -> list[str] | None:
    fn = getattr(predictor, "predict_labels", None)
    if not callable(fn):
        return None
    prev = universe.snapshots[-2] if len(universe.snapshots) > 1 else None
    vec = metric_vector(projected, node_metrics(projected))
    return fn(vec, _snapshot_delta(prev, projected), universe.velocity_commits_per_week)


def graph_slice(snapshot: Snapshot) -> dict:
    return {
        "commit_sha": snapshot.commit_sha,
        "authored_at": snapshot.authored_at,
        "nodes": [n.model_dump() for n in snapshot.nodes],
        "edges": [e.model_dump() for e in snapshot.edges],
        "contracts": [c.model_dump() for c in snapshot.contracts],
    }
