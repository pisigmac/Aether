"use client";

import { EmptyState } from "@/components/EmptyState";
import { GhostTable } from "@/components/GhostTable";
import { useForecast } from "@/components/ForecastProvider";

export default function GhostsPage() {
  const { bundle, loading } = useForecast();
  if (loading) return <p className="text-mist">Attaching feature intents…</p>;
  if (!bundle) return <EmptyState />;
  return <GhostTable ghosts={bundle.ghosts} />;
}
