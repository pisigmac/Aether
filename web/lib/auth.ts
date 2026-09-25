const TOKEN_KEY = "aether.access_token";

export function authBase() {
  return process.env.NEXT_PUBLIC_AUTH_URL || "http://127.0.0.1:8090";
}

export function getAccessToken() {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(TOKEN_KEY) || "";
}

export function setAccessToken(token: string) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

export type AuthSession = {
  sub: string;
  email: string;
  orgId: string;
};

export function readSession(): AuthSession | null {
  const token = getAccessToken();
  if (!token) return null;
  const payload = decodePayload(token);
  if (!payload) return null;
  return {
    sub: String(payload.sub || ""),
    email: String(payload.email || ""),
    orgId: String(payload.org_id || ""),
  };
}

export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  if (!token) return {};
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  const session = readSession();
  if (session?.orgId) headers["X-Org-ID"] = session.orgId;
  return headers;
}

export async function loginWithOpenDesk(email: string, password: string) {
  const res = await fetch(`${authBase()}/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = (await res.json()) as { access_token?: string };
  if (!data.access_token) throw new Error("OpenDesk did not return an access token");
  setAccessToken(data.access_token);
}

export function oauthStart(provider: "google" | "github") {
  return `${authBase()}/v1/oauth/${provider}/start`;
}

function decodePayload(token: string): Record<string, unknown> | null {
  const part = token.split(".")[1];
  if (!part) return null;
  try {
    const padded = part.replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(padded.padEnd(padded.length + ((4 - (padded.length % 4)) % 4), "="));
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}
