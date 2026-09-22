from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from aether_sdk.pressure import Band, pressure_band


class IngestResult(BaseModel):
    universe_id: str
    repo_path: str
    license: str = ""
    snapshots: int = 0
    velocity_commits_per_week: float = 1.0
    warnings: list[str] = Field(default_factory=list)


class JobAccepted(BaseModel):
    job_id: str
    status: str
    percent: int = 0
    stage: str = "queued"


class JobStatus(BaseModel):
    job_id: str
    status: str
    percent: int = 0
    stage: str = ""
    error: str = ""
    result: IngestResult | None = None

    @property
    def done(self) -> bool:
        return self.status == "done"

    @property
    def failed(self) -> bool:
        return self.status == "error"


class UniverseSummary(BaseModel):
    id: str
    repo_path: str
    license: str = ""
    velocity: float = 1.0


class NodeMetrics(BaseModel):
    node_id: str
    kind: str
    label: str
    path: str = ""
    lang: str = ""
    mass: float
    velocity: float
    momentum: float
    pressure: float
    dependents: int = 0

    @property
    def band(self) -> Band:
        return pressure_band(self.pressure)


class Collision(BaseModel):
    a: str
    b: str
    reason: str
    intensity: float


class TimelineFrame(BaseModel):
    t_index: int
    months_ahead: float
    label: str
    cells: list[NodeMetrics] = Field(default_factory=list)
    collisions: list[Collision] = Field(default_factory=list)
    narrative: str = ""
    narrative_kind: Literal["rising_pressure", "bottleneck", "stable"] = "stable"

    def hottest(self, n: int = 8) -> list[NodeMetrics]:
        return sorted(self.cells, key=lambda c: c.pressure, reverse=True)[:n]

    def by_band(self) -> dict[Band, list[NodeMetrics]]:
        out: dict[Band, list[NodeMetrics]] = {"calm": [], "watch": [], "high-pressure": []}
        for cell in self.cells:
            out[cell.band].append(cell)
        return out


class ImpactedNode(BaseModel):
    node_id: str
    label: str
    kind: str
    intensity: float
    path_type: str = ""


class ButterflyFrame(BaseModel):
    months: float
    origin_ids: list[str] = Field(default_factory=list)
    impacted: list[ImpactedNode] = Field(default_factory=list)


class GhostResult(BaseModel):
    intent: str
    title: str
    verdict: Literal["pass", "warn", "fail"]
    extensibility: float
    files_touched: list[str] = Field(default_factory=list)
    core_mass_hits: list[str] = Field(default_factory=list)
    new_cycles: int = 0
    contract_breaks: list[str] = Field(default_factory=list)
    note: str = ""


class CostBand(BaseModel):
    month: int
    compute: float
    storage: float
    egress: float
    drivers: list[str] = Field(default_factory=list)


class Forecast(BaseModel):
    universe_id: str
    repo_path: str
    ir_version: int = 1
    horizon_months: int = 24
    velocity_commits_per_week: float = 1.0
    timeline: list[TimelineFrame] = Field(default_factory=list)
    butterflies: list[ButterflyFrame] = Field(default_factory=list)
    ghosts: list[GhostResult] = Field(default_factory=list)
    costs: list[CostBand] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    heuristic: bool = True
    license: str = ""

    def frame(self, months: float = 8) -> TimelineFrame | None:
        if not self.timeline:
            return None
        return min(self.timeline, key=lambda f: abs(f.months_ahead - months))

    def hottest(self, n: int = 8, months: float = 8) -> list[NodeMetrics]:
        frame = self.frame(months)
        return frame.hottest(n) if frame else []

    def storms(self, months: float = 8) -> list[Collision]:
        frame = self.frame(months)
        return list(frame.collisions) if frame else []


class Mutation(BaseModel):
    op: Literal["add", "remove", "retarget"]
    node: dict[str, Any] | None = None
    edge: dict[str, Any] | None = None
    retarget_src: str = ""
    retarget_dst: str = ""


class ChangeSet(BaseModel):
    id: str = ""
    universe_id: str = ""
    label: str = "changeset"
    summary: str = ""
    mutations: list[Mutation] = Field(default_factory=list)
    touched_paths: list[str] = Field(default_factory=list)


class GraphSlice(BaseModel):
    commit_sha: str = ""
    authored_at: str = ""
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    contracts: list[dict[str, Any]] = Field(default_factory=list)
