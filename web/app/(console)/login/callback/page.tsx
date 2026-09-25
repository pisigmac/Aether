"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { setAccessToken } from "@/lib/auth";

export default function LoginCallbackPage() {
  const router = useRouter();
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const access = params.get("access_token");
    if (access) {
      setAccessToken(access);
      router.replace("/ingest");
      return;
    }
    router.replace("/login");
  }, [router]);
  return <p className="text-sm text-mist">Completing sign-in…</p>;
}
