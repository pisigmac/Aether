"use client";

import { useEffect, useState } from "react";
import {
  cancelJob,
  clearUniverseId,
  deleteUniverse,
  fetchAudit,
  fetchJobs,
  fetchUniverses,
  type AuditRow,
  getUniverseId,
  ingestRepo,
  type UniverseSummary,
} from "@/lib/api";
import { useForecast } from "@/components/ForecastProvider";
import type { JobStatus } from "@/lib/types";

export default function IngestPage() {
  const { reload } = useForecast();
  const [path, setPath] = useState("../fixtures/polyglot-debt");
  const [url, setUrl] = useState("");
  const [pr, setPr] = useState("");
  const [velocity, setVelocity] = useState("");
  const [samplePolicy, setSamplePolicy] = useState("even");
  const [sampleEvery, setSampleEvery] = useState("10");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [percent, setPercent] = useState(0);
  const [stage, setStage] = useState("");
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [jobsError, setJobsError] = useState("");
  const [jobId, setJobId] = useState("");
  const [universes, setUniverses] = useState<UniverseSummary[]>([]);
  const [universesError, setUniversesError] = useState("");
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [auditError, setAuditError] = useState("");

  const demos = [
    { name: "clsx", url: "https://github.com/lukeed/clsx" },
    { name: "markupsafe", url: "https://github.com/pallets/markupsafe" },
    { name: "httpcore", url: "https://github.com/encode/httpcore" },
  ];

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setPercent(0);
    setStage("Queued");
    setStatus("Starting ingest…");
    try {
      const result = await ingestRepo(
        {
          path: path || undefined,
          url: url || undefined,
          pr_ref: pr || undefined,
          velocity_override: velocity ? Number(velocity) : null,
          sample_policy: samplePolicy,
          sample_every: samplePolicy === "every" ? Number(sampleEvery) || 1 : 1,
        },
        (nextPercent, nextStage) => {
          setPercent(nextPercent);
          setStage(nextStage);
          setStatus(`${nextPercent}% · ${nextStage}`);
        },
        setJobId,
      );
      setPercent(100);
      setStage("Forecast ready");
      await reload();
      setStatus(
        `Universe ${result.universe_id} · ${result.snapshots} snapshots · ${result.sample_policy} · ${result.velocity_commits_per_week} commits/week`
      );
      void refreshJobs();
      void refreshUniverses();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "ingest failed");
      void refreshJobs();
    } finally {
      setBusy(false);
    }
  }

  async function refreshJobs() {
    try {
      setJobs(await fetchJobs());
      setJobsError("");
    } catch (err) {
      setJobsError(err instanceof Error ? err.message : "Could not load jobs");
    }
  }

  async function refreshUniverses() {
    try {
      setUniverses(await fetchUniverses());
      setUniversesError("");
    } catch (err) {
      setUniversesError(err instanceof Error ? err.message : "Could not load universes");
    }
  }

  async function refreshAudit() {
    try {
      setAudit(await fetchAudit());
      setAuditError("");
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : "Could not load the audit log");
    }
  }

  async function onDelete(id: string) {
    try {
      await deleteUniverse(id);
      if (getUniverseId() === id) {
        clearUniverseId();
        await reload();
      }
      await refreshUniverses();
    } catch (err) {
      setUniversesError(err instanceof Error ? err.message : "Could not delete universe");
    }
  }

  useEffect(() => {
    void refreshJobs();
    void refreshUniverses();
    void refreshAudit();
    const timer = window.setInterval(() => {
      void refreshJobs();
      void refreshUniverses();
      void refreshAudit();
    }, 2000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="space-y-6">
    <form onSubmit={onSubmit} className="card max-w-2xl space-y-4 p-6">
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">Ingest</p>
        <h2 className="text-xl">Feed Aether a repo</h2>
        <p className="mt-1 text-sm text-mist">
          Local path or a public git URL. License must be MIT / Apache-2.0 / BSD. No scrape.
        </p>
      </div>
      <label className="block text-sm">
        Local path
        <input
          className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="/abs/path/to/repo"
        />
      </label>
      <label className="block text-sm">
        Git URL (optional)
        <input
          className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/org/repo"
        />
      </label>
      <label className="block text-sm">
        PR ref or planted_pr.json path (optional)
        <input
          className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
          value={pr}
          onChange={(e) => setPr(e.target.value)}
        />
      </label>
      <label className="block text-sm">
        Snapshot sampling
        <select
          className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
          value={samplePolicy}
          onChange={(e) => setSamplePolicy(e.target.value)}
        >
          <option value="even">Even across history</option>
          <option value="weekly">One commit per week</option>
          <option value="every">Every Nth commit</option>
          <option value="tag">Tags only</option>
        </select>
      </label>
      {samplePolicy === "every" ? (
        <label className="block text-sm">
          N
          <input
            className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
            value={sampleEvery}
            min={1}
            type="number"
            onChange={(e) => setSampleEvery(e.target.value)}
          />
        </label>
      ) : null}
      <label className="block text-sm">
        Velocity override, commits/week
        <input
          className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
          value={velocity}
          onChange={(e) => setVelocity(e.target.value)}
        />
      </label>
      <div className="flex flex-wrap gap-2">
        {demos.map((demo) => (
          <button
            key={demo.name}
            type="button"
            className="rounded-lg border border-white/10 px-3 py-1.5 font-mono text-xs text-sky-100 hover:bg-white/5"
            onClick={() => {
              setPath("");
              setUrl(demo.url);
            }}
          >
            {demo.name}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-3">
      <button
        disabled={busy}
        className="rounded-lg bg-sky-500/30 px-4 py-2 text-sky-50 disabled:opacity-50"
      >
        {busy ? `${percent}% · ${stage || "Working"}` : "Run forecast"}
      </button>
      {busy && jobId && (
        <button
          type="button"
          className="rounded-lg border border-rose-300/40 px-4 py-2 text-sm text-rose-200"
          onClick={() => {
            void cancelJob(jobId).catch((err) => {
              setStatus(err instanceof Error ? err.message : "cancel failed");
            });
          }}
        >
          Cancel
        </button>
      )}
      </div>
      {(busy || percent > 0) && (
        <div>
          <div className="mb-1 flex items-center justify-between font-mono text-xs text-sky-200">
            <span>{stage || "Queued"}</span>
            <span>{percent}%</span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-white/10"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percent}
            aria-label={stage || "Ingest progress"}
          >
            <div
              className="h-full rounded-full bg-sky-400 transition-[width] duration-300"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
      )}
      {status && <p className="font-mono text-xs text-mist">{status}</p>}
      <p className="text-xs text-mist">
        Demo path: the polyglot-debt fixture. Dogfood path: this Aether repo (Python engine + TypeScript
        dashboard).
      </p>
    </form>
    <section className="card max-w-2xl space-y-3 p-6">
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">Universes</p>
        <h2 className="text-lg">This org</h2>
      </div>
      {universesError ? (
        <p className="text-sm text-rose-300">{universesError}</p>
      ) : universes.length === 0 ? (
        <p className="text-sm text-mist">No universes for this org yet.</p>
      ) : (
        <ol className="space-y-2">
          {universes.map((row) => (
            <li key={row.id} className="flex items-center justify-between gap-3 rounded-lg border border-white/10 px-3 py-2">
              <div className="min-w-0">
                <p className="truncate font-mono text-xs text-sky-100">{row.repo_path}</p>
                <p className="mt-1 truncate text-xs text-mist">{row.org_id || "local"} · {row.id}</p>
              </div>
              <button
                type="button"
                className="shrink-0 rounded-lg border border-rose-300/40 px-3 py-1.5 text-xs text-rose-200"
                onClick={() => {
                  if (!window.confirm("Delete this universe?")) return;
                  void onDelete(row.id);
                }}
              >
                Delete
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
    <section className="card max-w-2xl space-y-3 p-6">
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">Audit</p>
        <h2 className="text-lg">Who ingested what</h2>
      </div>
      {auditError ? (
        <p className="text-sm text-rose-300">{auditError}</p>
      ) : audit.length === 0 ? (
        <p className="text-sm text-mist">No ingests recorded yet.</p>
      ) : (
        <ol className="space-y-2">
          {audit.map((row) => (
            <li key={row.id} className="rounded-lg border border-white/10 px-3 py-2">
              <div className="flex items-center justify-between gap-3 font-mono text-xs">
                <span className="truncate text-sky-100">{row.actor}</span>
                <span className="shrink-0 text-mist">{row.decision} · {row.license}</span>
              </div>
              <p className="mt-1 truncate text-xs text-mist">{row.target}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
    <section className="card max-w-2xl space-y-3 p-6">
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">Jobs</p>
        <h2 className="text-lg">Recent ingests</h2>
      </div>
      {jobsError ? (
        <p className="text-sm text-rose-300">{jobsError}</p>
      ) : jobs.length === 0 ? (
        <p className="text-sm text-mist">No ingest jobs yet.</p>
      ) : (
        <ol className="space-y-2">
          {jobs.map((job) => (
            <li key={job.job_id} className="rounded-lg border border-white/10 px-3 py-2">
              <div className="flex items-center justify-between gap-3 font-mono text-xs">
                <span className="truncate text-sky-100">{job.label || job.job_id}</span>
                <span className="shrink-0 text-mist">
                  {job.status} · {job.percent}%
                </span>
              </div>
              <p className="mt-1 truncate text-xs text-mist">{job.stage}</p>
              {job.error && <p className="mt-1 text-xs text-rose-300">{job.error}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
    </div>
  );
}
