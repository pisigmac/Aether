"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { authBase, loginWithOpenDesk, oauthStart } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await loginWithOpenDesk(email, password);
      router.push("/ingest");
    } catch (err) {
      setError(err instanceof Error ? err.message : "OpenDesk sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card max-w-md space-y-4 p-6">
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-sky-300/80">OpenDesk</p>
        <h2 className="text-xl">Sign in</h2>
        <p className="mt-1 text-sm text-mist">
          The password goes to OpenDesk at {authBase()}. Aether only keeps the access token.
        </p>
      </div>
      <div className="flex gap-2">
        <a className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-sky-100 hover:bg-white/5" href={oauthStart("google")}>
          Google
        </a>
        <a className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-sky-100 hover:bg-white/5" href={oauthStart("github")}>
          GitHub
        </a>
      </div>
      <label className="block text-sm">
        Email
        <input
          className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </label>
      <label className="block text-sm">
        Password
        <input
          className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2"
          type="password"
          value={password}
          minLength={8}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      <button
        type="submit"
        disabled={busy}
        className="rounded-lg bg-[#e7a15a] px-4 py-2 text-sm font-medium text-black disabled:opacity-60"
      >
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
