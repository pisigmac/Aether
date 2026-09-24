"use client";

import { CostChart } from "@/components/CostChart";
import { EmptyState } from "@/components/EmptyState";
import { useForecast } from "@/components/ForecastProvider";

export default function CostPage() {
  const { bundle, loading } = useForecast();
  if (loading) return <p className="text-mist">Pricing the forecast…</p>;
  if (!bundle) return <EmptyState />;
  return <CostChart costs={bundle.costs} />;
}
