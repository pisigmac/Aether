"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import type { ButterflyFrame } from "@/lib/types";
import { pressureColor } from "@/lib/pressure";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export function ButterflyGraph({ frames }: { frames: ButterflyFrame[] }) {
  const [idx, setIdx] = useState(() => Math.min(2, Math.max(frames.length - 1, 0)));
  const frame = frames[idx] ?? frames[0];

  const graph = useMemo(() => {
    if (!frame) return { nodes: [], links: [] };
    const nodes = frame.impacted.map((n) => ({
      id: n.node_id,
      name: n.label,
      kind: n.kind,
      path_type: n.path_type,
      val: 2 + n.intensity * 4,
      intensity: n.intensity,
    }));
    const origin = new Set(frame.origin_ids);
    const links = frame.impacted
      .filter((n) => !origin.has(n.node_id))
      .slice(0, 24)
      .map((n) => ({
        source: frame.origin_ids[0] || n.node_id,
        target: n.node_id,
      }));
    return { nodes, links };
  }, [frame]);

  if (!frame) {
    return <p className="text-mist">No butterfly data yet. Ingest a repo first.</p>;
  }

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">Blast radius</p>
          <h2 className="text-xl">Butterfly at {frame.months === 0 ? "now" : `+${frame.months} months`}</h2>
        </div>
        <div className="flex gap-2">
          {frames.map((f, i) => (
            <button
              key={f.months}
              onClick={() => setIdx(i)}
              className={`rounded-md px-3 py-1 text-sm ${
                i === idx ? "bg-sky-500/20 text-sky-100" : "text-mist hover:bg-white/5"
              }`}
            >
              {f.months === 0 ? "now" : `+${f.months}mo`}
            </button>
          ))}
        </div>
      </div>
      <div className="h-[520px]">
        <ForceGraph2D
          graphData={graph}
          backgroundColor="#07111c"
          nodeLabel={(n: any) => `${n.name} (${n.path_type || n.kind})`}
          nodeColor={(n: any) => pressureColor(n.intensity)}
          linkColor={() => "rgba(159,179,200,0.35)"}
          nodeRelSize={5}
        />
      </div>
      <ul className="grid gap-2 border-t border-white/10 p-5 md:grid-cols-2">
        {frame.impacted.slice(0, 8).map((n) => (
          <li key={n.node_id} className="text-sm text-mist">
            <span className="text-white">{n.label}</span> · {n.path_type || n.kind} · intensity{" "}
            {n.intensity.toFixed(2)}
          </li>
        ))}
      </ul>
    </div>
  );
}
