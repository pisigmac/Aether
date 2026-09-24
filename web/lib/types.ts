export type NarrativeKind = "rising_pressure" | "bottleneck" | "stable";

export type NodeMetrics = {
  node_id: string;
  kind: string;
  label: string;
  path: string;
  lang: string;
  mass: number;
  velocity: number;
  momentum: number;
  pressure: number;
  pressure_lo?: number;
  pressure_hi?: number;
  dependents: number;
};

export type Collision = {
  a: string;
  b: string;
  reason: string;
  intensity: number;
};

export type TimelineFrame = {
  t_index: number;
  months_ahead: number;
  label: string;
  cells: NodeMetrics[];
  collisions: Collision[];
  narrative: string;
  narrative_kind: NarrativeKind;
};

export type ImpactedNode = {
  node_id: string;
  label: string;
  kind: string;
  intensity: number;
  path_type: string;
};

export type ButterflyFrame = {
  months: number;
  origin_ids: string[];
  impacted: ImpactedNode[];
};

export type GhostResult = {
  intent: string;
  title: string;
  verdict: "pass" | "warn" | "fail";
  extensibility: number;
  files_touched: string[];
  core_mass_hits: string[];
  new_cycles: number;
  contract_breaks: string[];
  note: string;
  session_id?: string;
  budget?: number;
  trace_id?: string;
  trace_url?: string;
  artifact_path?: string;
  fail_reason?: string;
  ir_only?: boolean;
  ir_mutation?: string;
};

export type GhostRun = {
  parallel: number;
  duration_ms: number;
  disclosure: string;
  sandbox: string;
  ghosts: GhostResult[];
};

export type CostBand = {
  month: number;
  compute: number;
  storage: number;
  egress: number;
  drivers: string[];
};

export type ForecastBundle = {
  universe_id: string;
  repo_path: string;
  ir_version: number;
  horizon_months: number;
  velocity_commits_per_week: number;
  timeline: TimelineFrame[];
  butterflies: ButterflyFrame[];
  ghosts: GhostResult[];
  costs: CostBand[];
  warnings: string[];
  heuristic: boolean;
  license: string;
  model_id?: string;
  training_records?: number;
};

export type IngestResponse = {
  universe_id: string;
  repo_path: string;
  license: string;
  snapshots: number;
  velocity_commits_per_week: number;
  warnings: string[];
};

export type JobStatus = {
  job_id: string;
  status: "queued" | "running" | "done" | "error" | "cancelled";
  percent: number;
  stage: string;
  error: string;
  result: IngestResponse | null;
  created_at?: string;
  label?: string;
};
