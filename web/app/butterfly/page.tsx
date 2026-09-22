"use client";

import { ButterflyGraph } from "@/components/ButterflyGraph";
import { EmptyState } from "@/components/EmptyState";
import { useForecast } from "@/components/ForecastProvider";

export default function ButterflyPage() {
  const { bundle, loading } = useForecast();
  if (loading) return <p className="text-mist">Tracing blast fronts…</p>;
  if (!bundle) return <EmptyState />;
  return (
    <div className="space-y-4">
      <p className="text-sm text-mist">
        Click the month chips to watch a schema change walk into frontend contracts. Foggy /
        unresolved edges stay unlabeled — Aether does not invent certainty.
      </p>
      <ButterflyGraph frames={bundle.butterflies} />
    </div>
  );
}
