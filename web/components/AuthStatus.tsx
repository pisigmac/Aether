"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { clearAccessToken, readSession, type AuthSession } from "@/lib/auth";

export function AuthStatus() {
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    setSession(readSession());
  }, []);

  if (!session) {
    return (
      <Link href="/login" className="rounded-lg px-3 py-2 text-sm text-mist hover:bg-white/5">
        Sign in
      </Link>
    );
  }

  const label = session.email || session.sub;
  const org = session.orgId ? ` · ${session.orgId}` : "";
  return (
    <button
      type="button"
      className="rounded-lg px-3 py-2 text-sm text-mist hover:bg-white/5"
      onClick={() => {
        clearAccessToken();
        setSession(null);
      }}
    >
      {label}
      {org}
    </button>
  );
}
