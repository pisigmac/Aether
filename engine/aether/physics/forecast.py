from __future__ import annotations

from aether.ir.models import ChangeSet, ForecastBundle, Snapshot, Universe
from aether.physics.butterfly import apply_changeset, origins_from_changeset, propagate
from aether.physics.cost import build_costs
from aether.physics.ghosts import run_ghost_lab
from aether.physics.time_machine import build_timeline


def build_forecast(
    universe: Universe,
    horizon_months: int = 24,
    changeset: ChangeSet | None = None,
    extra_warnings: list[str] | None = None,
) -> ForecastBundle:
    if not universe.snapshots:
        raise ValueError("Universe has no snapshots to forecast.")
    latest = universe.snapshots[-1]
    projected = apply_changeset(latest, changeset)
    timeline = build_timeline(universe.snapshots, horizon_months, universe.velocity_commits_per_week)
    origins = origins_from_changeset(projected, changeset)
    butterflies = [propagate(projected, origins, m) for m in (0.0, 3.0, 8.0, 24.0) if m <= horizon_months]
    ghosts = run_ghost_lab(projected)
    costs = build_costs(projected, horizon_months, universe.velocity_commits_per_week)
    warnings = [
        "Heuristic forecast from this repo's own history — not trained on millions of repositories.",
        *(extra_warnings or []),
    ]
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
        heuristic=True,
        license=universe.license,
    )


def graph_slice(snapshot: Snapshot) -> dict:
    return {
        "commit_sha": snapshot.commit_sha,
        "authored_at": snapshot.authored_at,
        "nodes": [n.model_dump() for n in snapshot.nodes],
        "edges": [e.model_dump() for e in snapshot.edges],
        "contracts": [c.model_dump() for c in snapshot.contracts],
    }
