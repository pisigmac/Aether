import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from aether.api import app
from aether.config import Settings, settings
from aether.gates.guardloop import GuardLoopClient, GuardLoopError, GuardLoopGate, LoopOutcome, ScrubOutcome
from aether.ir.models import Node, NodeKind
from aether.physics.ghosts import CATALOG, AgentGhostRunner, run_ghost_lab
from tests.test_api import _universe
from tests.test_physics import _snap

SECRET = "AKIAIOSFODNN7EXAMPLE"


class _Handler(BaseHTTPRequestHandler):
    seen: list[dict] = []
    iterations = 0

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        body = json.loads(raw.decode()) if raw else {}
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        _Handler.seen.append(
            {
                "path": parsed.path,
                "body": body,
                "query": query,
                "authorization": self.headers.get("Authorization", ""),
            }
        )
        if parsed.path == "/tasks":
            self._send({"id": "task-1", "max_loops": body.get("max_loops")})
            return
        if parsed.path == "/tasks/task-1/start":
            self._send({"status": "started", "task_id": "task-1"})
            return
        if parsed.path == "/pii/scrub":
            text = body.get("context_text", "")
            blocked = SECRET in text
            scrubbed = text.replace(SECRET, "[AWS_ACCESS_KEY_REDACTED]")
            self._send(
                {
                    "scrubbed_text": scrubbed,
                    "blocked": blocked,
                    "block_reason": "Strict mode: 1 secrets found and blocked." if blocked else None,
                    "secrets_count": 1 if blocked else 0,
                }
            )
            return
        if parsed.path == "/tasks/task-1/loop-check":
            _Handler.iterations += 1
            self._send(
                {
                    "iterations": _Handler.iterations,
                    "should_halt": False,
                    "warnings": [],
                    "status": "healthy",
                }
            )
            return
        self._send({"detail": "not found"}, 404)

    def _send(self, payload: dict, code: int = 200) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def _server() -> ThreadingHTTPServer:
    _Handler.seen = []
    _Handler.iterations = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_settings_do_not_hold_a_guardloop_key():
    assert "guardloop_url" in Settings.model_fields
    assert "tracelens_url" in Settings.model_fields
    assert "guardloop_api_key" not in Settings.model_fields
    assert "tracelens_api_key" not in Settings.model_fields
    assert "api_key" not in Settings.model_fields


def test_default_lab_does_not_call_guardloop():
    server = _server()
    try:
        ghosts = run_ghost_lab(_snap("a", "2026-01-01T00:00:00+00:00"))
        assert all("attach via" in ghost.note.lower() for ghost in ghosts)
        assert _Handler.seen == []
    finally:
        server.shutdown()


def test_agent_session_uses_one_task_budget_scrub_and_loop_check():
    server = _server()
    host, port = server.server_address
    try:
        client = GuardLoopClient(f"http://{host}:{port}", api_key="gl_live_test_key")
        ghosts = run_ghost_lab(
            _snap("a", "2026-01-01T00:00:00+00:00"),
            AgentGhostRunner(GuardLoopGate(client), budget=len(CATALOG)),
        )
        assert len(ghosts) == len(CATALOG)
        assert {ghost.session_id for ghost in ghosts} == {"task-1"}
        assert {ghost.budget for ghost in ghosts} == {len(CATALOG)}
        assert all(ghost.note.startswith("Agent run:") for ghost in ghosts)
        creates = [item for item in _Handler.seen if item["path"] == "/tasks"]
        assert creates[0]["body"]["max_loops"] == len(CATALOG)
        assert creates[0]["body"]["name"] == "aether-ghost-lab"
        assert creates[0]["authorization"] == "Bearer gl_live_test_key"
        assert sum(item["path"] == "/pii/scrub" for item in _Handler.seen) == len(CATALOG)
        assert sum(item["path"] == "/tasks/task-1/loop-check" for item in _Handler.seen) == len(CATALOG)
        assert any(item["path"] == "/tasks/task-1/start" for item in _Handler.seen)
    finally:
        server.shutdown()


def test_secret_scrub_halts_and_does_not_echo_the_secret():
    server = _server()
    host, port = server.server_address
    try:
        snap = _snap("a", "2026-01-01T00:00:00+00:00")
        snap.nodes[1] = Node(
            id="cpy",
            kind=NodeKind.CONTRACT,
            lang="python",
            path=f"secret/{SECRET}.py",
            export_name=SECRET,
            loc=10,
        )
        client = GuardLoopClient(f"http://{host}:{port}")
        ghosts = run_ghost_lab(snap, AgentGhostRunner(GuardLoopGate(client), budget=8))
        rendered = " ".join(ghost.note for ghost in ghosts) + " ".join(
            path for ghost in ghosts for path in ghost.files_touched
        )
        assert SECRET not in rendered
        assert ghosts[0].verdict == "fail"
        assert "GuardLoop halted" in ghosts[0].note
        checks = [item for item in _Handler.seen if item["path"] == "/tasks/task-1/loop-check"]
        assert checks == []
        scrub = next(item for item in _Handler.seen if item["path"] == "/pii/scrub")
        assert scrub["body"]["strict_mode"] is True
    finally:
        server.shutdown()


def test_loop_budget_stops_later_intents():
    class _BudgetGate:
        def __init__(self):
            self.checks = 0

        def open(self, name: str, budget: int) -> str:
            assert budget == 2
            return "sess"

        def scrub(self, session_id: str, text: str) -> ScrubOutcome:
            return ScrubOutcome(text=text, blocked=False, reason="", secrets=0)

        def check(self, session_id: str, context: str, action: str) -> LoopOutcome:
            self.checks += 1
            return LoopOutcome(should_halt=False, iterations=self.checks, warnings=())

    gate = _BudgetGate()
    ghosts = run_ghost_lab(_snap("a", "2026-01-01T00:00:00+00:00"), AgentGhostRunner(gate, budget=2))
    assert gate.checks == 3
    assert all(ghost.note.startswith("Agent run: attached") for ghost in ghosts[:2])
    assert "loop budget 2 exhausted" in ghosts[2].note
    assert all(ghost.verdict == "fail" for ghost in ghosts[2:])


def test_client_error_does_not_include_the_key():
    server = _server()
    host, port = server.server_address

    class _Down(_Handler):
        def do_POST(self) -> None:  # noqa: N802
            self._send({"detail": "no"}, 500)

    server.RequestHandlerClass = _Down
    try:
        client = GuardLoopClient(f"http://{host}:{port}", api_key="gl_live_secret_value")
        try:
            client.create_task("aether-ghost-lab", 4)
        except GuardLoopError as exc:
            assert "gl_live_secret_value" not in str(exc)
            assert "HTTP 500" in str(exc)
        else:
            raise AssertionError("expected GuardLoopError")
    finally:
        server.shutdown()


def test_ghost_endpoint_is_gated_and_leaves_forecast_heuristic(tmp_path, monkeypatch):
    server = _server()
    host, port = server.server_address
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "model_path", None)
    monkeypatch.setattr(settings, "guardloop_url", "")
    _universe(tmp_path / "aether.db")
    try:
        with TestClient(app) as client:
            missing = client.post("/v1/universes/u1/ghosts")
            assert missing.status_code == 503
            monkeypatch.setattr(settings, "guardloop_url", f"http://{host}:{port}")
            gated = client.post(
                f"/v1/universes/u1/ghosts?budget={len(CATALOG)}",
                headers={"X-GuardLoop-Key": "gl_live_header"},
            )
            assert gated.status_code == 200
            body = gated.json()
            rows = body["ghosts"]
            assert body["parallel"] == 4
            assert "hard max 16" in body["disclosure"]
            assert body["sandbox"]
            assert rows[0]["session_id"] == "task-1"
            assert rows[0]["ir_only"] is True
            assert rows[0]["artifact_path"]
            assert _Handler.seen[0]["body"]["name"] == "aether-ghost:u1"
            assert rows[0]["budget"] == len(CATALOG)
            forecast = client.get("/v1/universes/u1/forecast")
            assert forecast.status_code == 200
            assert all("attach via" in ghost["note"].lower() for ghost in forecast.json()["ghosts"])
            assert all(item["authorization"] == "Bearer gl_live_header" for item in _Handler.seen)
    finally:
        server.shutdown()
