"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CloudRain, GitGraph, Ghost, DollarSign, UploadCloud } from "lucide-react";
import { useForecast } from "@/components/ForecastProvider";

const LINKS = [
  { href: "/", label: "Radar", icon: CloudRain },
  { href: "/butterfly", label: "Butterfly", icon: GitGraph },
  { href: "/ghosts", label: "Ghost Lab", icon: Ghost },
  { href: "/cost", label: "Cost Horizon", icon: DollarSign },
  { href: "/ingest", label: "Ingest", icon: UploadCloud },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const { bundle, mode, setMode, learnedAvailable } = useForecast();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-[#07111c]/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-sky-300/80">Aether</p>
            <h1 className="text-lg font-medium">Software weather forecast</h1>
          </div>
          <div className="flex items-center gap-3">
            {bundle && learnedAvailable && (
              <div className="flex rounded-lg border border-white/10 p-0.5 font-mono text-xs">
                <button
                  type="button"
                  onClick={() => setMode("heuristic")}
                  className={`rounded-md px-2.5 py-1 ${
                    mode === "heuristic" || (mode === "auto" && bundle.heuristic)
                      ? "bg-white/10 text-white"
                      : "text-mist hover:bg-white/5"
                  }`}
                >
                  Heuristic
                </button>
                <button
                  type="button"
                  onClick={() => setMode("learned")}
                  className={`rounded-md px-2.5 py-1 ${
                    mode === "learned" || (mode === "auto" && !bundle.heuristic)
                      ? "bg-white/10 text-white"
                      : "text-mist hover:bg-white/5"
                  }`}
                >
                  Learned
                </button>
              </div>
            )}
          <nav className="flex gap-1">
            {LINKS.map((link) => {
              const Icon = link.icon;
              const active = path === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                    active ? "bg-white/10 text-white" : "text-mist hover:bg-white/5"
                  }`}
                >
                  <Icon size={16} />
                  {link.label}
                </Link>
              );
            })}
          </nav>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
