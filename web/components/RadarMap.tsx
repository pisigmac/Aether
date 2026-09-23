"use client";

import { pressureColor, pressureLabel } from "@/lib/pressure";
import type { TimelineFrame } from "@/lib/types";

export function RadarMap({ frame }: { frame: TimelineFrame }) {
  const cells = [...frame.cells].sort((a, b) => b.pressure - a.pressure);
  const shown = cells.slice(0, 24);
  const hidden = Math.max(cells.length - shown.length, 0);
  const storms = new Set(frame.collisions.flatMap((c) => [c.a, c.b]));

  return (
    <div className="card p-5">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">Radar</p>
          <h2 className="text-xl">High-pressure zones</h2>
          {hidden > 0 && (
            <p className="mt-1 font-mono text-xs text-mist">
              Hottest 24 of {cells.length} modules
            </p>
          )}
        </div>
        <p className="max-w-md text-right text-sm text-mist">{frame.narrative}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
        {shown.map((cell) => {
          const size = 48 + Math.min(cell.mass, 12) * 6;
          const storm = storms.has(cell.node_id);
          const lo = cell.pressure_lo ?? cell.pressure;
          const hi = cell.pressure_hi ?? cell.pressure;
          const fog = hi - lo >= 0.6;
          return (
            <div
              key={cell.node_id}
              className={`relative overflow-hidden rounded-lg border border-white/10 p-3 ${fog ? "opacity-45" : ""}`}
              style={{
                background: `linear-gradient(180deg, ${pressureColor(cell.pressure)}22, transparent)`,
              }}
            >
              <div
                className="mb-2 rounded-full"
                style={{
                  width: size,
                  height: 10,
                  background: pressureColor(cell.pressure),
                  boxShadow: storm ? `0 0 16px ${pressureColor(cell.pressure)}` : undefined,
                }}
              />
              <p className="truncate text-sm font-medium">{cell.label}</p>
              <p className="font-mono text-xs text-mist">
                {cell.kind} · {pressureLabel(cell.pressure)} · P {cell.pressure.toFixed(2)}
              </p>
              {fog && <p className="mt-1 text-xs text-mist">fog · wide pressure band</p>}
              {storm && <p className="mt-1 text-xs text-amber-300">storm / predicted collision</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
