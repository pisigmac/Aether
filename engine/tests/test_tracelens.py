import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fastapi.testclient import TestClient

from aether.api import app
from aether.config import settings
from aether.gates.tracelens import TraceLensClient, TraceLensTracer
from aether.physics.ghosts import AgentGhostRunner, run_ghost_lab
from tests.test_api import _universe
from tests.test_physics import _snap


class _Handler(BaseHTTPRequestHandler):
    spans: list[dict] = []

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length).decode()) if length else {}
        _Handler.spans.append(
            {"path": self.path, "body": body, "authorization": self.headers.get("Authorization", "")}
        )
        raw = json.dumps({"ingested": len(body.get("spans") or []), "trace_id": body.get("trace_id")}).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def test_agent_session_posts_one_trace():
    _Handler.spans = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    try:
        tracer = TraceLensTracer(
            TraceLensClient(f"http://{host}:{port}", api_key="header.payload.sig"),
            dashboard_url="http://127.0.0.1:43000",
        )
        ghosts = run_ghost_lab(_snap("a", "2026-01-01T00:00:00+00:00"), AgentGhostRunner(tracer=tracer))
        assert len({ghost.trace_id for ghost in ghosts}) == 1
        trace_id = ghosts[0].trace_id
        assert ghosts[0].trace_url == f"http://127.0.0.1:43000/traces/{trace_id}"
        assert len(_Handler.spans) == 8
        assert {item["body"]["trace_id"] for item in _Handler.spans} == {trace_id}
        assert _Handler.spans[0]["authorization"] == "Bearer header.payload.sig"
        assert _Handler.spans[0]["body"]["spans"][0]["agent_type"] == "aether-ghost"
        assert "header.payload.sig" not in json.dumps(_Handler.spans[0]["body"])
    finally:
        server.shutdown()


def test_heuristic_forecast_is_not_traced(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "model_path", None)
    monkeypatch.setattr(settings, "guardloop_url", "http://127.0.0.1:9")
    monkeypatch.setattr(settings, "tracelens_url", "http://127.0.0.1:9")
    monkeypatch.setattr(settings, "tracelens_dashboard_url", "http://127.0.0.1:43000")
    _universe(tmp_path / "aether.db")
    with TestClient(app) as client:
        denied = client.post("/v1/universes/u1/ghosts")
        assert denied.status_code == 401
        forecast = client.get("/v1/universes/u1/forecast")
        assert forecast.status_code == 200
        assert all(ghost["trace_id"] == "" for ghost in forecast.json()["ghosts"])
        assert all("attach via" in ghost["note"].lower() for ghost in forecast.json()["ghosts"])
