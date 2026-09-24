"use client";

import { useState } from "react";
import { runAgentGhosts } from "@/lib/api";
import type { GhostResult, GhostRun } from "@/lib/types";
import { GhostTable } from "./GhostTable";

export function GhostLab({
  universeId,
  heuristic,
}: {
  universeId: string;
  heuristic: GhostResult[];
}) {
  const [parallel, setParallel] = useState(4);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [run, setRun] = useState<GhostRun | null>(null);

  async function onRun() {
    setBusy(true);
    setError("");
    try {
      setRun(await runAgentGhosts(universeId, parallel, 50, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="card space-y-4 p-5">
        <p className="text-sm text-mist">
          4 ghosts run in parallel by default, hard max 16. The heuristic table stays. An agent run
          writes only inside a sandbox worktree.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm">
            Parallel
            <input
              className="mt-1 block w-24 rounded-md border border-white/10 bg-black/30 px-3 py-2"
              type="number"
              min={1}
              max={16}
              value={parallel}
              onChange={(event) => setParallel(Number(event.target.value))}
            />
          </label>
          <label className="min-w-[16rem] flex-1 text-sm">
            TraceLens token
            <input
              className="mt-1 block w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
              type="password"
              value={token}
              autoComplete="off"
              placeholder="Only if the engine requires it"
              onChange={(event) => setToken(event.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-lg border border-white/10 px-3 py-2 font-mono text-xs text-sky-100 hover:bg-white/5 disabled:opacity-50"
            disabled={busy}
            onClick={onRun}
          >
            {busy ? "Running…" : "Run agent ghosts"}
          </button>
        </div>
        {error && <p className="text-sm text-rose-200">{error}</p>}
        {run && (
          <p className="text-sm text-mist">
            {run.disclosure} Duration {run.duration_ms} ms. Sandbox {run.sandbox}
          </p>
        )}
      </div>
      {run && <GhostTable ghosts={run.ghosts} />}
      <GhostTable ghosts={heuristic} />
    </div>
  );
}
