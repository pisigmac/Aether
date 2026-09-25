import { authHeaders } from "./auth";
import type { ForecastBundle, GhostRun, IngestResponse, JobStatus } from "./types";

const API = process.env.NEXT_PUBLIC_AETHER_API || "http://localhost:8000";
const UNIVERSE_KEY = "aether.universe_id";

export function apiBase() {
  return API;
}

export function getUniverseId() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(UNIVERSE_KEY) || "";
}

export function setUniverseId(id: string) {
  localStorage.setItem(UNIVERSE_KEY, id);
}

export async function startIngestJob(body: {
  path?: string;
  url?: string;
  pr_ref?: string;
  velocity_override?: number | null;
  sample_policy?: string;
  sample_every?: number;
}): Promise<{ job_id: string }> {
  const res = await fetch(`${API}/v1/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function cancelJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API}/v1/jobs/${jobId}/cancel`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function fetchJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API}/v1/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export type AuditRow = {
  id: string;
  at: string;
  actor: string;
  org_id: string;
  target: string;
  license: string;
  decision: string;
  universe_id: string;
};

export async function fetchAudit(): Promise<AuditRow[]> {
  const res = await fetch(`${API}/v1/audit`, { headers: authHeaders() });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function fetchJobs(): Promise<JobStatus[]> {
  const res = await fetch(`${API}/v1/jobs`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function ingestRepo(
  body: {
    path?: string;
    url?: string;
    pr_ref?: string;
    velocity_override?: number | null;
    sample_policy?: string;
    sample_every?: number;
  },
  onProgress?: (percent: number, stage: string) => void,
  onJob?: (jobId: string) => void,
): Promise<IngestResponse> {
  const { job_id } = await startIngestJob(body);
  onJob?.(job_id);
  for (;;) {
    const job = await fetchJob(job_id);
    onProgress?.(job.percent, job.stage);
    if (job.status === "cancelled") {
      throw new Error("Ingest cancelled");
    }
    if (job.status === "done" && job.result) {
      setUniverseId(job.result.universe_id);
      return job.result;
    }
    if (job.status === "error") {
      throw new Error(job.error || "ingest failed");
    }
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
}

export type ForecastMode = "auto" | "heuristic" | "learned";

export type PredictorInfo = {
  name: string;
  model_id: string;
  training_records: number;
  learned_available: boolean;
};

export type UniverseSummary = {
  id: string;
  repo_path: string;
  license: string;
  velocity: number;
  org_id: string;
};

export async function fetchUniverses(): Promise<UniverseSummary[]> {
  const res = await fetch(`${API}/v1/universes`, { headers: authHeaders() });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function deleteUniverse(universeId: string): Promise<void> {
  const res = await fetch(`${API}/v1/universes/${universeId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
}

export function clearUniverseId() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(UNIVERSE_KEY);
}

export async function fetchForecast(
  universeId: string,
  horizon = 24,
  mode: ForecastMode = "auto",
): Promise<ForecastBundle> {
  const res = await fetch(
    `${API}/v1/universes/${universeId}/forecast?horizon_months=${horizon}&mode=${mode}`,
    { headers: authHeaders() },
  );
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function fetchPredictor(): Promise<PredictorInfo> {
  const res = await fetch(`${API}/v1/predictor`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function runAgentGhosts(
  universeId: string,
  parallel = 4,
  budget = 50,
  tracelensKey = "",
): Promise<GhostRun> {
  const headers: Record<string, string> = { ...authHeaders() };
  if (tracelensKey) headers["X-TraceLens-Key"] = tracelensKey;
  const res = await fetch(
    `${API}/v1/universes/${universeId}/ghosts?budget=${budget}&parallel=${parallel}`,
    { method: "POST", headers },
  );
  if (!res.ok) {
    const text = await res.text();
    let message = text;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // keep the raw response text
    }
    throw new Error(message);
  }
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API}/health`);
  return res.json();
}
