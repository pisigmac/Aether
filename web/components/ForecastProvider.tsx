"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { fetchForecast, getUniverseId } from "@/lib/api";
import type { ForecastBundle } from "@/lib/types";

type Ctx = {
  bundle: ForecastBundle | null;
  error: string;
  loading: boolean;
  reload: () => Promise<void>;
};

const ForecastContext = createContext<Ctx>({
  bundle: null,
  error: "",
  loading: false,
  reload: async () => {},
});

export function ForecastProvider({ children }: { children: React.ReactNode }) {
  const [bundle, setBundle] = useState<ForecastBundle | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const reload = async () => {
    const id = getUniverseId();
    if (!id) {
      setBundle(null);
      setError("");
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setBundle(await fetchForecast(id));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "forecast failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
  }, []);

  return (
    <ForecastContext.Provider value={{ bundle, error, loading, reload }}>
      {children}
    </ForecastContext.Provider>
  );
}

export function useForecast() {
  return useContext(ForecastContext);
}
