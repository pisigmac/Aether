import type { ForecastBundle, IngestResponse, JobStatus } from "./types";

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
}): Promise<{ job_id: string }> {
  const res = await fetch(`${API}/v1/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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

export async function ingestRepo(
  body: {
    path?: string;
    url?: string;
    pr_ref?: string;
    velocity_override?: number | null;
  },
  onProgress?: (percent: number, stage: string) => void,
): Promise<IngestResponse> {
  const { job_id } = await startIngestJob(body);
  for (;;) {
    const job = await fetchJob(job_id);
    onProgress?.(job.percent, job.stage);
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

export async function fetchForecast(universeId: string, horizon = 24): Promise<ForecastBundle> {
  const res = await fetch(`${API}/v1/universes/${universeId}/forecast?horizon_months=${horizon}`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API}/health`);
  return res.json();
}
