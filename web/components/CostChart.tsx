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
            <XAxis dataKey="month" stroke="#9fb3c8" tickFormatter={(v) => `+${v}m`} />
            <YAxis stroke="#9fb3c8" />
            <Tooltip
              contentStyle={{ background: "#0d1b2a", border: "1px solid rgba(255,255,255,0.1)" }}
            />
            <Area type="monotone" dataKey="compute" stackId="1" stroke="#3d9ee0" fill="#3d9ee055" />
            <Area type="monotone" dataKey="storage" stackId="1" stroke="#d4a017" fill="#d4a01744" />
            <Area type="monotone" dataKey="egress" stackId="1" stroke="#e05a4f" fill="#e05a4f33" />
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
