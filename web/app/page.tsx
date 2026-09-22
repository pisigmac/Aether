"use client";

import { useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { PressureGuide } from "@/components/PressureGuide";
import { RadarMap } from "@/components/RadarMap";
import { TimeScrubber } from "@/components/TimeScrubber";
import { useForecast } from "@/components/ForecastProvider";

export default function RadarPage() {
  const { bundle, error, loading } = useForecast();
  const [index, setIndex] = useState(0);

  if (loading) return <p className="text-mist">Reading the atmosphere…</p>;
  if (error) return <EmptyState message={error} />;
  if (!bundle) return <EmptyState />;

  const frame = bundle.timeline[index] ?? bundle.timeline[0];
  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-sm text-mist">{bundle.repo_path.split("/").filter(Boolean).slice(-1)[0]}</p>
          <p className="font-mono text-xs text-mist">
            {bundle.velocity_commits_per_week} commits/week · {bundle.horizon_months}-month horizon
          </p>
        </div>
      </div>
      <PressureGuide />
      {frame && <RadarMap frame={frame} />}
      <TimeScrubber frames={bundle.timeline} index={index} onChange={setIndex} />
    </div>
  );
}
