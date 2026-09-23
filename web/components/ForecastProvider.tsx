"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { fetchForecast, fetchPredictor, getUniverseId, type ForecastMode } from "@/lib/api";
import type { ForecastBundle } from "@/lib/types";

type Ctx = {
  bundle: ForecastBundle | null;
  error: string;
  loading: boolean;
  mode: ForecastMode;
  setMode: (mode: ForecastMode) => void;
  learnedAvailable: boolean;
  reload: () => Promise<void>;
};

const ForecastContext = createContext<Ctx>({
  bundle: null,
  error: "",
  loading: false,
  mode: "auto",
  setMode: () => {},
  learnedAvailable: false,
  reload: async () => {},
});

export function ForecastProvider({ children }: { children: React.ReactNode }) {
  const [bundle, setBundle] = useState<ForecastBundle | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<ForecastMode>("auto");
  const [learnedAvailable, setLearnedAvailable] = useState(false);
  const requestId = useRef(0);

  const reload = async (nextMode = mode) => {
    const id = getUniverseId();
    const ticket = ++requestId.current;
    if (!id) {
      if (ticket !== requestId.current) return;
      setBundle(null);
      setError("");
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const info = await fetchPredictor().catch(() => null);
      const next = await fetchForecast(id, 24, nextMode);
      if (ticket !== requestId.current) return;
      setLearnedAvailable(Boolean(info?.learned_available));
      setBundle(next);
      setError("");
    } catch (err) {
      if (ticket !== requestId.current) return;
      setError(err instanceof Error ? err.message : "forecast failed");
    } finally {
      if (ticket === requestId.current) setLoading(false);
    }
  };

  useEffect(() => {
    void reload(mode);
  }, [mode]);

  return (
    <ForecastContext.Provider
      value={{ bundle, error, loading, mode, setMode, learnedAvailable, reload: () => reload(mode) }}
    >
      {children}
    </ForecastContext.Provider>
  );
}

export function useForecast() {
  return useContext(ForecastContext);
}
