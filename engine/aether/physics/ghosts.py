from __future__ import annotations

from dataclasses import dataclass

from aether.ir.models import GhostResult, NodeKind, Snapshot
from aether.physics.metrics import node_metrics


@dataclass(frozen=True)
class GhostIntent:
    intent: str
    title: str
    prefers: tuple[str, ...]
    avoid_kinds: tuple[str, ...]


CATALOG: list[GhostIntent] = [
    GhostIntent("add_crud_resource", "Add CRUD resource", ("module", "contract"), ("service",)),
    GhostIntent("add_pagination", "Add pagination", ("contract",), ("schema",)),
    GhostIntent("add_webhook", "Add webhook", ("module", "contract"), ("schema",)),
    GhostIntent("add_cache_layer", "Add cache layer", ("module",), ("schema",)),
    GhostIntent("split_module", "Split a god module", ("module",), ("contract",)),
    GhostIntent("add_authz", "Add authorization", ("module", "contract"), ()),
    GhostIntent("add_index", "Add schema index", ("schema",), ("contract",)),
    GhostIntent("add_event_bus", "Add event bus", ("module",), ("schema",)),
]


class GhostRunner:
    """Seam for later real agents. Phase 1 is a heuristic planner."""

    def run(self, snapshot: Snapshot, intent: GhostIntent) -> GhostResult:
        cells = {c.node_id: c for c in node_metrics(snapshot)}
        ranked = sorted(cells.values(), key=lambda c: c.mass, reverse=True)
        attach = [c for c in ranked if c.kind in intent.prefers][:4]
        if not attach:
            attach = ranked[:2]
        files = list(dict.fromkeys(c.path for c in attach if c.path))
        core = [c.label for c in attach if c.mass >= 3.0 or c.kind == "service"]
        new_cycles = 1 if any(c.pressure > 1.4 for c in attach) else 0
        breaks: list[str] = []
        if intent.intent == "add_pagination":
            unbounded = [
                n.export_name
                for n in snapshot.nodes
                if n.kind == NodeKind.CONTRACT and n.export_name.rstrip("/").endswith("s")
            ]
            if unbounded:
                breaks.append(f"Must change contract {unbounded[0]}")
        if intent.intent == "split_module":
            gods = [c for c in ranked if c.kind == "module" and c.mass > 4]
            if gods:
                core = [gods[0].label]
                files = [gods[0].path] if gods[0].path else files

        hits = len(core) + new_cycles + len(breaks)
        score = max(0.05, 1.0 - hits * 0.18 - len(files) * 0.04)
        if score >= 0.72:
            verdict: str = "pass"
        elif score >= 0.45:
            verdict = "warn"
        else:
            verdict = "fail"
        note = (
            f"Would attach via {', '.join(c.label for c in attach[:3]) or 'no obvious seam'}."
        )
        return GhostResult(
            intent=intent.intent,
            title=intent.title,
            verdict=verdict,  # type: ignore[arg-type]
            extensibility=round(score, 3),
            files_touched=files[:8],
            core_mass_hits=core[:6],
            new_cycles=new_cycles,
            contract_breaks=breaks,
            note=note,
        )


def run_ghost_lab(snapshot: Snapshot) -> list[GhostResult]:
    runner = GhostRunner()
    return [runner.run(snapshot, intent) for intent in CATALOG]
