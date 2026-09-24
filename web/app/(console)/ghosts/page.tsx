"use client";

import { EmptyState } from "@/components/EmptyState";
import { GhostLab } from "@/components/GhostLab";
import { useForecast } from "@/components/ForecastProvider";

export default function GhostsPage() {
  const { bundle, loading } = useForecast();
  if (loading) return <p className="text-mist">Attaching feature intents…</p>;
  if (!bundle) return <EmptyState />;
  return <GhostLab universeId={bundle.universe_id} heuristic={bundle.ghosts} />;
}
