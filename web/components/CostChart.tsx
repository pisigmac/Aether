"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CostBand } from "@/lib/types";

export function CostChart({ costs }: { costs: CostBand[] }) {
  const drivers = costs[0]?.drivers ?? [];
  return (
    <div className="card p-5">
      <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">Financial reality check</p>
      <h2 className="mb-4 text-xl">24-month cost horizon</h2>
      <div className="h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={costs}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="month" stroke="#b7aa93" tickFormatter={(v) => `+${v}m`} />
            <YAxis stroke="#b7aa93" />
            <Tooltip
              contentStyle={{ background: "#10160f", border: "1px solid rgba(243,236,223,0.12)", color: "#f3ecdf" }}
            />
            <Area type="monotone" dataKey="compute" stackId="1" stroke="#7dbea8" fill="#7dbea855" />
            <Area type="monotone" dataKey="storage" stackId="1" stroke="#e7a15a" fill="#e7a15a44" />
            <Area type="monotone" dataKey="egress" stackId="1" stroke="#e36b5a" fill="#e36b5a33" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 text-sm text-mist">
        Drivers from this repo: {drivers.join(", ") || "none detected"}. Units are relative cloud-cost
        bands from <code>datasets/cost_drivers.json</code>, not a vendor invoice.
      </p>
    </div>
  );
}
