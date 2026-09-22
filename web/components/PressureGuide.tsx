const BANDS = [
  {
    name: "Calm",
    range: "P < 0.6",
    color: "#3d9ee0",
    impact: "This module is stable. Agents can land features without raising structural risk.",
    action: "Keep shipping. Re-forecast after the next large PR.",
  },
  {
    name: "Watch",
    range: "P 0.6–1.2",
    color: "#d4a017",
    impact: "Debt is forming — coupling, churn, or a leaky contract. Eight months out it becomes a bottleneck.",
    action: "Add pagination, indexes, or tests before the next agent wave. Open Butterfly on the cell.",
  },
  {
    name: "High-pressure",
    range: "P ≥ 1.2",
    color: "#e05a4f",
    impact: "A core module or schema will fail the next feature cycle. Cost and collisions climb together.",
    action: "Split the god module, fix the contract, or block the schema change. Do not pile more agents here.",
  },
  {
    name: "Storm",
    range: "collision",
    color: "#f59e0b",
    impact: "Two change vectors share a contract — typically schema → API → frontend.",
    action: "Scrub to +8 months, then open Butterfly and cut that path.",
  },
];

export function PressureGuide() {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {BANDS.map((band) => (
        <div key={band.name} className="card p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: band.color }} />
            <p className="font-medium">{band.name}</p>
            <span className="font-mono text-xs text-mist">{band.range}</span>
          </div>
          <p className="text-xs text-mist">
            <span className="text-white/80">Impact. </span>
            {band.impact}
          </p>
          <p className="mt-2 text-xs text-sky-200/90">
            <span className="text-white/80">Action. </span>
            {band.action}
          </p>
        </div>
      ))}
    </div>
  );
}
