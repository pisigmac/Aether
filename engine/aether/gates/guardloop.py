"""HTTP client for GuardLoop. Credentials are supplied by the caller (KeyMint), never read from Aether settings."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


class GuardLoopError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScrubOutcome:
    text: str
    blocked: bool
    reason: str
    secrets: int


@dataclass(frozen=True)
class LoopOutcome:
    should_halt: bool
    iterations: int
    warnings: tuple[str, ...]


class GuardLoopClient:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 10.0):
        if not base_url:
            raise GuardLoopError("GuardLoop URL is not configured")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout = timeout

    def create_task(self, name: str, max_loops: int) -> str:
        payload = self._request(
            "POST",
            "/tasks",
            {"name": name, "description": "Aether ghost session", "max_loops": max_loops, "priority": 5},
        )
        task_id = str(payload.get("id") or "")
        if not task_id:
            raise GuardLoopError("GuardLoop did not return a task id")
        return task_id

    def start_task(self, task_id: str) -> None:
        self._request("POST", f"/tasks/{urllib.parse.quote(task_id)}/start", {})

    def scrub(self, task_id: str, text: str, strict: bool = True) -> ScrubOutcome:
        payload = self._request(
            "POST",
            "/pii/scrub",
            {"task_id": task_id, "context_text": text, "strict_mode": strict},
        )
        return ScrubOutcome(
            text=str(payload.get("scrubbed_text") or ""),
            blocked=bool(payload.get("blocked")),
            reason=str(payload.get("block_reason") or ""),
            secrets=int(payload.get("secrets_count") or 0),
        )

    def loop_check(self, task_id: str, context: str, action: str) -> LoopOutcome:
        payload = self._request(
            "POST",
            f"/tasks/{urllib.parse.quote(task_id)}/loop-check",
            query={"context_text": context, "action_summary": action},
        )
        warnings = payload.get("warnings") or []
        return LoopOutcome(
            should_halt=bool(payload.get("should_halt")),
            iterations=int(payload.get("iterations") or 0),
            warnings=tuple(str(item) for item in warnings),
        )

    def _request(self, method: str, path: str, body: dict | None = None, query: dict | None = None) -> dict:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            raise GuardLoopError(f"GuardLoop HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise GuardLoopError("GuardLoop connection failed") from exc
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise GuardLoopError("GuardLoop returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise GuardLoopError("GuardLoop returned an unexpected payload")
        return parsed


class GuardLoopGate:
    """One GuardLoop task per ghost session: budget, scrub, then loop check."""

    def __init__(self, client: GuardLoopClient):
        self.client = client

    def open(self, name: str, budget: int) -> str:
        task_id = self.client.create_task(name, budget)
        self.client.start_task(task_id)
        return task_id

    def scrub(self, session_id: str, text: str) -> ScrubOutcome:
        return self.client.scrub(session_id, text, strict=True)

    def check(self, session_id: str, context: str, action: str) -> LoopOutcome:
        return self.client.loop_check(session_id, context, action)
