"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CloudRain, GitGraph, Ghost, DollarSign, UploadCloud } from "lucide-react";
import { useForecast } from "@/components/ForecastProvider";
import { AuthStatus } from "@/components/AuthStatus";
import { LiveBar } from "@/components/LiveBar";
import { AetherLogo, HomeLink } from "@/components/Logo";

const LINKS = [
  { href: "/radar", label: "Radar", icon: CloudRain },
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
      <header className="sticky top-0 z-20 border-b border-white/10 bg-[#141910]/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <AetherLogo />
            <h1 className="mt-1 font-display text-lg font-medium">Software weather forecast</h1>
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
          <AuthStatus />
          <nav className="flex gap-1">
            <HomeLink
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                path === "/" ? "bg-white/10 text-white" : "text-mist hover:bg-white/5"
              }`}
            >
              Home
            </HomeLink>
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
      <main className="mx-auto max-w-6xl px-6 py-8 pb-40">{children}</main>
      <LiveBar />
    </div>
  );
}
