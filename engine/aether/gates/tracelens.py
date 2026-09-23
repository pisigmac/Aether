"""HTTP client for TraceLens. The bearer JWT is supplied by the caller, never read from Aether settings."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Protocol


class TraceLensError(RuntimeError):
    pass


class GhostTracer(Protocol):
    def open(self, name: str) -> str: ...

    def span(self, trace_id: str, name: str, status: str, note: str) -> None: ...

    def url(self, trace_id: str) -> str: ...


class TraceLensClient:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 10.0):
        if not base_url:
            raise TraceLensError("TraceLens URL is not configured")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout = timeout

    def ingest(self, trace_id: str, span: dict) -> None:
        self._request("POST", "/v1/spans", {"trace_id": trace_id, "spans": [span]})

    def _request(self, method: str, path: str, body: dict) -> dict:
        data = json.dumps(body).encode()
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            raise TraceLensError(f"TraceLens HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise TraceLensError("TraceLens connection failed") from exc
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TraceLensError("TraceLens returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise TraceLensError("TraceLens returned an unexpected payload")
        return parsed


class TraceLensTracer:
    """One trace id per ghost session. TraceLens does not mint ids."""

    def __init__(self, client: TraceLensClient, dashboard_url: str = ""):
        self.client = client
        self.dashboard_url = dashboard_url.rstrip("/")
        self._parent = ""

    def open(self, name: str) -> str:
        return uuid.uuid4().hex

    def url(self, trace_id: str) -> str:
        if not self.dashboard_url or not trace_id:
            return ""
        return f"{self.dashboard_url}/traces/{trace_id}"

    def span(self, trace_id: str, name: str, status: str, note: str) -> None:
        span_id = uuid.uuid4().hex
        failed = status == "error"
        self.client.ingest(
            trace_id,
            {
                "span_id": span_id,
                "parent_id": self._parent or None,
                "agent_type": "aether-ghost",
                "tool_name": name,
                "status": "error" if failed else "ok",
                "error_message": note if failed else None,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "attributes": {"session": name, "note": note},
            },
        )
        if not self._parent:
            self._parent = span_id
