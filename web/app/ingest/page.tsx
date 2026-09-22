"use client";

import { useState } from "react";
import { ingestRepo } from "@/lib/api";
import { useForecast } from "@/components/ForecastProvider";

export default function IngestPage() {
  const { reload } = useForecast();
  const [path, setPath] = useState("../fixtures/polyglot-debt");
  const [url, setUrl] = useState("");
  const [pr, setPr] = useState("");
  const [velocity, setVelocity] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [percent, setPercent] = useState(0);
  const [stage, setStage] = useState("");

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
        },
        (nextPercent, nextStage) => {
          setPercent(nextPercent);
          setStage(nextStage);
          setStatus(`${nextPercent}% · ${nextStage}`);
        },
      );
      setPercent(100);
      setStage("Forecast ready");
      await reload();
      setStatus(
        `Universe ${result.universe_id} · ${result.snapshots} snapshots · ${result.velocity_commits_per_week} commits/week`
      );
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "ingest failed");
    } finally {
      setBusy(false);
    }
  }

  return (
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
        Velocity override, commits/week
        <input
          className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
          value={velocity}
          onChange={(e) => setVelocity(e.target.value)}
        />
      </label>
      <button
        disabled={busy}
        className="rounded-lg bg-sky-500/30 px-4 py-2 text-sky-50 disabled:opacity-50"
      >
        {busy ? `${percent}% · ${stage || "Working"}` : "Run forecast"}
      </button>
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
  );
}
