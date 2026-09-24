from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from aether.gates.guardloop import LoopOutcome, ScrubOutcome
from aether.gates.tracelens import GhostTracer
from aether.ir.models import Edge, EdgeKind, GhostResult, Node, NodeKind, Snapshot
from aether.physics.metrics import _cycles, node_metrics, snapshot_graph
from aether.physics.sandbox import write_ghost_artifact

MAX_GHOST_PARALLEL = 16
DEFAULT_GHOST_PARALLEL = 4


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
PHASE1_INTENTS = tuple(item.intent for item in CATALOG)
CATALOG.extend(
    [
        GhostIntent("add_openapi_client", "Add OpenAPI client", ("contract",), ("schema",)),
        GhostIntent("extract_service", "Extract a service", ("module",), ("schema",)),
        GhostIntent("add_queue", "Add a queue", ("module",), ("schema",)),
    ]
)


class GhostRunner(Protocol):
    name: str

    def run(self, snapshot: Snapshot, intent: GhostIntent) -> GhostResult: ...


class GhostGate(Protocol):
    def open(self, name: str, budget: int) -> str: ...

    def scrub(self, session_id: str, text: str) -> ScrubOutcome: ...

    def check(self, session_id: str, context: str, action: str) -> LoopOutcome: ...


class HeuristicGhostRunner:
    """Rank attach points by mass. Default Ghost Lab planner."""

    name = "heuristic"

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


class AgentGhostRunner:
    """Attach each catalog intent as a shadow IR node. Does not write the checkout.

    When a gate is attached, the catalog shares one GuardLoop session: a loop budget,
    a secret scrub, and a loop check. An optional tracer records that same session
    in TraceLens. The default lab does not use a gate or a tracer.
    """

    name = "agent"

    def __init__(
        self,
        gate: GhostGate | None = None,
        budget: int = 50,
        session_name: str = "aether-ghost-lab",
        tracer: GhostTracer | None = None,
        sandbox: Path | None = None,
    ):
        if budget < 1 or budget > 500:
            raise ValueError("ghost session budget must be between 1 and 500")
        self.gate = gate
        self.budget = budget
        self.session_name = session_name
        self.tracer = tracer
        self.sandbox = sandbox
        self.session_id = ""
        self.trace_id = ""
        self._halted = False
        self._halt_reason = ""
        self._lock = threading.Lock()

    def run(self, snapshot: Snapshot, intent: GhostIntent) -> GhostResult:
        result = self._attach(snapshot, intent)
        result = self._materialize(result)
        with self._lock:
            if self.gate is not None:
                result = self._guard(result, intent)
            if self.tracer is not None:
                result = self._trace(result)
        return result

    def _attach(self, snapshot: Snapshot, intent: GhostIntent) -> GhostResult:
        before = (len(snapshot.nodes), len(snapshot.edges))
        target = _attach_target(snapshot, intent)
        ghost_id = f"ghost:{intent.intent}"
        shadow = snapshot.model_copy(deep=True)
        shadow.nodes.append(
            Node(
                id=ghost_id,
                kind=NodeKind.MODULE,
                lang="python",
                path=f"ghost/{intent.intent}.py",
                export_name=intent.intent,
                loc=40,
                complexity=4,
            )
        )
        if target is not None:
            shadow.edges.append(Edge(src=target.id, dst=ghost_id, kind=EdgeKind.IMPORT))
        _, cycles_before = _cycles(snapshot_graph(snapshot))
        _, cycles_after = _cycles(snapshot_graph(shadow))
        new_cycles = max(0, cycles_after - cycles_before)
        pressure = 0.0
        if target is not None:
            cells = {cell.node_id: cell for cell in node_metrics(snapshot)}
            found = cells.get(target.id)
            pressure = found.pressure if found else 0.0
        files = [f"ghost/{intent.intent}.py"]
        if target is not None and target.path:
            files.append(target.path)
        hot = pressure >= 1.2
        hits = new_cycles + int(hot)
        score = max(0.05, 1.0 - hits * 0.25)
        if score >= 0.72:
            verdict: str = "pass"
        elif score >= 0.45:
            verdict = "warn"
        else:
            verdict = "fail"
        where = target.export_name if target is not None and target.export_name else "a new module"
        mutation = f"add module {ghost_id}"
        if target is not None:
            mutation += f" import {target.id}"
        assert (len(snapshot.nodes), len(snapshot.edges)) == before
        note = f"Agent run: attached {intent.title} on {where}."
        return GhostResult(
            intent=intent.intent,
            title=intent.title,
            verdict=verdict,  # type: ignore[arg-type]
            extensibility=round(score, 3),
            files_touched=files[:8],
            core_mass_hits=[where] if hot else [],
            new_cycles=new_cycles,
            contract_breaks=[],
            note=note,
            fail_reason=note if verdict == "fail" else "",
            ir_only=True,
            ir_mutation=mutation,
        )

    def _materialize(self, result: GhostResult) -> GhostResult:
        if self.sandbox is None:
            return result
        artifact = write_ghost_artifact(self.sandbox, result.intent)
        return result.model_copy(update={"artifact_path": str(artifact)})

    def _guard(self, result: GhostResult, intent: GhostIntent) -> GhostResult:
        assert self.gate is not None
        if self._halted:
            return self._halted_result(result)
        if not self.session_id:
            self.session_id = self.gate.open(self.session_name, self.budget)
        context = "\n".join(
            [intent.title, result.note, *result.files_touched, *result.core_mass_hits]
        )
        scrub = self.gate.scrub(self.session_id, context)
        safe = _without_secrets(result, context, scrub.text)
        if scrub.blocked:
            self._halted = True
            self._halt_reason = scrub.reason or "secret scrub blocked the session"
            return self._halted_result(safe)
        outcome = self.gate.check(self.session_id, scrub.text, intent.intent)
        if outcome.should_halt or outcome.iterations > self.budget:
            self._halted = True
            self._halt_reason = (
                "; ".join(outcome.warnings) if outcome.warnings else f"loop budget {self.budget} exhausted"
            )
            return self._halted_result(safe)
        return safe.model_copy(update={"session_id": self.session_id, "budget": self.budget})

    def _trace(self, result: GhostResult) -> GhostResult:
        assert self.tracer is not None
        if not self.trace_id:
            self.trace_id = self.tracer.open(self.session_name)
        status = "error" if result.verdict == "fail" else "ok"
        self.tracer.span(self.trace_id, result.intent, status, result.note)
        return result.model_copy(
            update={"trace_id": self.trace_id, "trace_url": self.tracer.url(self.trace_id)}
        )

    def _halted_result(self, result: GhostResult) -> GhostResult:
        return result.model_copy(
            update={
                "verdict": "fail",
                "note": f"Agent run: GuardLoop halted — {self._halt_reason}.",
                "files_touched": [],
                "core_mass_hits": [],
                "session_id": self.session_id,
                "budget": self.budget,
                "fail_reason": f"Agent run: GuardLoop halted — {self._halt_reason}.",
            }
        )


def _without_secrets(result: GhostResult, raw: str, scrubbed: str) -> GhostResult:
    if raw == scrubbed:
        return result
    files = [item for item in result.files_touched if item and item in scrubbed]
    hits = [item for item in result.core_mass_hits if item and item in scrubbed]
    note = result.note if result.note and result.note in scrubbed else (
        f"Agent run: attached {result.title}. GuardLoop scrubbed the session context."
    )
    return result.model_copy(update={"note": note, "files_touched": files, "core_mass_hits": hits})


def _attach_target(snapshot: Snapshot, intent: GhostIntent):
    preferred = [node for node in snapshot.nodes if node.kind.value in intent.prefers]
    pool = preferred or list(snapshot.nodes)
    return pool[0] if pool else None


def parallel_width(parallel: int) -> int:
    if parallel < 1 or parallel > MAX_GHOST_PARALLEL:
        raise ValueError(f"parallel ghosts must be between 1 and {MAX_GHOST_PARALLEL}")
    return parallel


def disclose_parallel(parallel: int) -> str:
    width = parallel_width(parallel)
    noun = "ghost runs" if width == 1 else "ghosts run"
    return f"{width} {noun} in parallel (hard max {MAX_GHOST_PARALLEL})."


def run_ghost_lab(
    snapshot: Snapshot,
    runner: GhostRunner | None = None,
    parallel: int = 1,
) -> list[GhostResult]:
    chosen = runner or HeuristicGhostRunner()
    width = parallel_width(parallel)
    if width == 1:
        return [chosen.run(snapshot, intent) for intent in CATALOG]
    with ThreadPoolExecutor(max_workers=width) as pool:
        futures = [pool.submit(chosen.run, snapshot, intent) for intent in CATALOG]
        return [future.result() for future in futures]
