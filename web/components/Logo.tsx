"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { MouseEvent, ReactNode } from "react";

function goHome(event: MouseEvent<HTMLAnchorElement>, path: string) {
  if (path !== "/") return;
  event.preventDefault();
  window.history.replaceState(null, "", "/");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

export function AetherMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#141910" />
      <circle cx="16" cy="16" r="11" fill="none" stroke="#f3ecdf" strokeWidth="1.4" />
      <ellipse cx="16" cy="16" rx="8" ry="4.5" fill="none" stroke="#e7a15a" strokeWidth="0.8" opacity="0.85" />
      <path d="M16 16 L16 6.5" stroke="#e7a15a" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="16" cy="16" r="1.7" fill="#f3ecdf" />
    </svg>
  );
}

export function AetherLogo({ className = "" }: { className?: string }) {
  const path = usePathname();
  return (
    <Link
      href="/"
      className={`flex items-center gap-2.5 ${className}`}
      aria-label="Aether home"
      onClick={(event) => goHome(event, path)}
    >
      <AetherMark />
      <span className="font-mono text-xs uppercase tracking-[0.22em] text-[#f3ecdf]">Aether</span>
    </Link>
  );
}

export function HomeLink({ className, children }: { className?: string; children: ReactNode }) {
  const path = usePathname();
  return (
    <Link
      href="/"
      aria-current={path === "/" ? "page" : undefined}
      className={className}
      onClick={(event) => goHome(event, path)}
    >
      {children}
    </Link>
  );
}
