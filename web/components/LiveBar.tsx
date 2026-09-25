"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useForecast } from "@/components/ForecastProvider";
import { fetchForecast, fetchJobs, fetchUniverses, getUniverseId, setUniverseId } from "@/lib/api";
import { pressureColor, pressureLabel } from "@/lib/pressure";
import type { ForecastBundle, JobStatus, NodeMetrics, TimelineFrame } from "@/lib/types";

function repoName(path: string) {
  const trimmed = path.replace(/\/+$/, "");
  return trimmed.split("/").pop() || trimmed || "repo";
}

function frameNearEight(bundle: ForecastBundle): TimelineFrame | undefined {
  return bundle.timeline.reduce<TimelineFrame | undefined>((best, frame) => {
    if (!best) return frame;
    return Math.abs(frame.months_ahead - 8) < Math.abs(best.months_ahead - 8) ? frame : best;
  }, undefined);
}

function hottestCells(frame: TimelineFrame) {
  return [...frame.cells].sort((a, b) => b.pressure - a.pressure);
}

function isStorm(frame: TimelineFrame, cell: NodeMetrics) {
  return frame.collisions.some((hit) => hit.a === cell.node_id || hit.b === cell.node_id);
}

export function LiveBar() {
  const { bundle: selected, mode, loading, reload } = useForecast();
  const [workspace, setWorkspace] = useState<ForecastBundle | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [jobsError, setJobsError] = useState("");
  const watching = useRef("");
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  useEffect(() => {
    let stop = false;
    async function tick() {
      try {
        const rows = await fetchJobs();
        if (stop) return;
        setJobsError("");
        const active = rows.find((row) => row.status === "queued" || row.status === "running");
        const newest = rows[0];
        setJob(active || (newest?.status === "error" ? newest : null));
        if (active) watching.current = active.job_id;
        const finished = rows.find((row) => row.job_id === watching.current);
        if (finished && finished.status === "done" && finished.result) {
          watching.current = "";
          if (getUniverseId() !== finished.result.universe_id) {
            setUniverseId(finished.result.universe_id);
            await reloadRef.current();
          }
        } else if (finished && (finished.status === "error" || finished.status === "cancelled")) {
          watching.current = "";
        }
      } catch (err) {
        if (!stop) setJobsError(err instanceof Error ? err.message : "Engine unreachable");
      }
    }
    void tick();
    const timer = window.setInterval(() => void tick(), 1500);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let stop = false;
    async function loadWorkspace() {
      try {
        const universes = await fetchUniverses();
        const checkout = universes.find((row) => repoName(row.repo_path) === "Aether");
        if (!checkout) {
          if (!stop) setWorkspace(null);
          return;
        }
        const forecast = await fetchForecast(checkout.id, 24, mode);
        if (!stop) setWorkspace(forecast);
      } catch {
        if (!stop) setWorkspace(null);
      }
    }
    void loadWorkspace();
    const timer = window.setInterval(() => void loadWorkspace(), 15000);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [mode]);

  const bundle = workspace || selected;
  const ingesting = job && (job.status === "queued" || job.status === "running");
  const frame = bundle ? frameNearEight(bundle) : undefined;
  const ranked = frame ? hottestCells(frame) : [];
  const hottest = ranked[0];
  const storm = Boolean(hottest && frame && isStorm(frame, hottest));
  const color = ingesting ? "#7eb6ff" : hottest ? pressureColor(hottest.pressure) : "#ffffff33";
  const width = ingesting ? `${Math.max(job.percent, 4)}%` : hottest ? "100%" : "0%";
  const name = bundle ? repoName(bundle.repo_path) : "Aether";

  let kicker = "Live bar";
  let title = "No forecast yet";
  let detail = "Ingest a repo. This bar fills when the worker finishes.";
  let href = "/ingest";
  let action = "Ingest";

  if (ingesting && job) {
    kicker = `${name} · background ingest`;
    title = `${job.percent}% · ${job.stage || "Queued"}`;
    detail = job.label || "The worker is cloning and parsing. Pressure stays hidden until a forecast exists.";
    href = "/ingest";
    action = "Watch";
  } else if (job?.status === "error" && !hottest) {
    kicker = `${name} · ingest failed`;
    title = job.error || job.stage || "Ingest failed";
    detail = "The worker stopped. No pressure number was invented for this run.";
    href = "/ingest";
    action = "Fix";
  } else if (hottest && frame) {
    const band = storm ? "storm" : pressureLabel(hottest.pressure);
    kicker = `${name} · ${frame.label} · ${bundle?.heuristic ? "heuristic" : "learned"}`;
    title = `${hottest.path || hottest.label} · ${band} · P ${hottest.pressure.toFixed(2)}`;
    detail = frame.narrative;
    href = "/radar";
    action = "Radar";
  } else if (loading) {
    kicker = name;
    title = "Reading the atmosphere…";
    detail = jobsError || "Loading the latest forecast.";
    href = "/radar";
    action = "Radar";
  } else if (jobsError) {
    detail = jobsError;
  }

  const others = !ingesting && frame ? ranked.slice(1, 4) : [];

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-[#141910]/95 backdrop-blur">
      <Link href={href} className="mx-auto block max-w-6xl px-6 py-3" aria-label={title}>
        <div className="flex items-center gap-4">
          <div
            className="h-1.5 w-40 shrink-0 overflow-hidden rounded-full bg-white/10"
            role={ingesting ? "progressbar" : undefined}
            aria-valuemin={ingesting ? 0 : undefined}
            aria-valuemax={ingesting ? 100 : undefined}
            aria-valuenow={ingesting && job ? job.percent : undefined}
          >
            <div
              className="h-full rounded-full transition-[width] duration-300"
              style={{ width, background: color }}
            />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-mono text-[11px] uppercase tracking-widest text-sky-300/80">{kicker}</p>
            <p className="truncate font-mono text-sm text-sky-100">{title}</p>
          </div>
          <span className="shrink-0 font-mono text-xs text-sky-200">{action}</span>
        </div>
        <p className="mt-1 truncate text-xs text-mist">{detail}</p>
        {others.length > 0 && frame && (
          <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-mist">
            {others.map((cell) => {
              const band = isStorm(frame, cell) ? "storm" : pressureLabel(cell.pressure);
              return (
                <span key={cell.node_id}>
                  <span style={{ color: pressureColor(cell.pressure) }}>{band}</span>
                  {`  ${cell.path || cell.label}  P ${cell.pressure.toFixed(2)}`}
                </span>
              );
            })}
          </p>
        )}
      </Link>
    </div>
  );
}
