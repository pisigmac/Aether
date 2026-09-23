from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

IR_VERSION = 1


class NodeKind(str, Enum):
    SERVICE = "service"
    MODULE = "module"
    SYMBOL = "symbol"
    CONTRACT = "contract"
    SCHEMA = "schema"


class EdgeKind(str, Enum):
    IMPORT = "import"
    CALL = "call"
    TYPE_REF = "type_ref"
    HTTP = "http"
    SQL = "sql"
    EVENT = "event"
    UNRESOLVED = "unresolved"


class Node(BaseModel):
    id: str
    kind: NodeKind
    lang: str = ""
    path: str = ""
    export_name: str = ""
    loc: int = 0
    complexity: int = 1
    extra: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    src: str
    dst: str
    kind: EdgeKind
    weight: float = 1.0


class Contract(BaseModel):
    id: str
    kind: Literal["http", "sql", "event"]
    name: str
    path: str = ""
    lang: str = ""
    detail: str = ""


class Snapshot(BaseModel):
    commit_sha: str
    authored_at: str
    snapshot_hash: str
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    contracts: list[Contract] = Field(default_factory=list)


class Universe(BaseModel):
    id: str
    repo_path: str
    ir_version: int = IR_VERSION
    license: str = ""
    snapshots: list[Snapshot] = Field(default_factory=list)
    velocity_commits_per_week: float = 1.0


class Mutation(BaseModel):
    op: Literal["add", "remove", "retarget"]
    node: Node | None = None
    edge: Edge | None = None
    retarget_src: str = ""
    retarget_dst: str = ""


class ChangeSet(BaseModel):
    id: str
    universe_id: str
    label: str = "changeset"
    summary: str = ""
    mutations: list[Mutation] = Field(default_factory=list)
    touched_paths: list[str] = Field(default_factory=list)


class MetricVector(BaseModel):
    mass: float = 0.0
    coupling: float = 0.0
    churn: float = 0.0
    cycles: int = 0
    god_module_count: int = 0
    contract_leak_count: int = 0


class EvolutionRecord(BaseModel):
    repo_id: str
    commit_sha: str
    authored_at: str
    snapshot_hash: str
    metric_vector: MetricVector
    pattern_labels: list[str] = Field(default_factory=list)
    delta_from_prev: dict[str, int] = Field(default_factory=dict)
    horizon_target: MetricVector | None = None


class NodeMetrics(BaseModel):
    node_id: str
    kind: str
    label: str
    path: str
    lang: str = ""
    mass: float
    velocity: float
    momentum: float
    pressure: float
    pressure_lo: float = 0.0
    pressure_hi: float = 0.0
    dependents: int = 0


class Collision(BaseModel):
    a: str
    b: str
    reason: str
    intensity: float


class TimelineFrame(BaseModel):
    t_index: int
    months_ahead: float
    label: str
    cells: list[NodeMetrics]
    collisions: list[Collision] = Field(default_factory=list)
    narrative: str = ""
    narrative_kind: Literal["rising_pressure", "bottleneck", "stable"] = "stable"


class ImpactedNode(BaseModel):
    node_id: str
    label: str
    kind: str
    intensity: float
    path_type: str = ""


class ButterflyFrame(BaseModel):
    months: float
    origin_ids: list[str]
    impacted: list[ImpactedNode]


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
    session_id: str = ""
    budget: int = 0
    trace_id: str = ""
    trace_url: str = ""


class CostBand(BaseModel):
    month: int
    compute: float
    storage: float
    egress: float
    drivers: list[str] = Field(default_factory=list)


class ForecastBundle(BaseModel):
    universe_id: str
    repo_path: str
    ir_version: int = IR_VERSION
    horizon_months: int = 24
    velocity_commits_per_week: float = 1.0
    timeline: list[TimelineFrame] = Field(default_factory=list)
    butterflies: list[ButterflyFrame] = Field(default_factory=list)
    ghosts: list[GhostResult] = Field(default_factory=list)
    costs: list[CostBand] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    heuristic: bool = True
    license: str = ""
    model_id: str = "heuristic"
    training_records: int = 0
