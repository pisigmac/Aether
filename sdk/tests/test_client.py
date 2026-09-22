from aether_sdk import Aether, AetherHTTPError, AetherJobError
from aether_sdk.models import Forecast
import httpx
import pytest


def _router(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/health":
        return httpx.Response(200, json={"status": "ok", "service": "aether-engine"})
    if path == "/v1/jobs" and request.method == "POST":
        return httpx.Response(200, json={"job_id": "job1", "status": "queued", "percent": 0, "stage": "queued"})
    if path == "/v1/jobs/job1":
        return httpx.Response(
            200,
            json={
                "job_id": "job1",
                "status": "done",
                "percent": 100,
                "stage": "done",
                "error": "",
                "result": {
                    "universe_id": "abc",
                    "repo_path": "/tmp/express",
                    "license": "MIT",
                    "snapshots": 1,
                    "velocity_commits_per_week": 1.0,
                    "warnings": [],
                },
            },
        )
    if path == "/v1/jobs/bad":
        return httpx.Response(
            200,
            json={"job_id": "bad", "status": "error", "percent": 40, "stage": "failed", "error": "license denied"},
        )
    if path == "/v1/universes/abc/forecast":
        return httpx.Response(
            200,
            json={
                "universe_id": "abc",
                "repo_path": "/tmp/express",
                "horizon_months": 24,
                "timeline": [
                    {
                        "t_index": 0,
                        "months_ahead": 0,
                        "label": "now",
                        "cells": [
                            {
                                "node_id": "n1",
                                "kind": "module",
                                "label": "lib/application.js",
                                "path": "lib/application.js",
                                "mass": 4.0,
                                "velocity": 1.0,
                                "momentum": 4.0,
                                "pressure": 1.8,
                            },
                            {
                                "node_id": "n2",
                                "kind": "module",
                                "label": "index.js",
                                "path": "index.js",
                                "mass": 1.0,
                                "velocity": 0.2,
                                "momentum": 0.2,
                                "pressure": 0.04,
                            },
                        ],
                        "collisions": [],
                        "narrative": "stable",
                        "narrative_kind": "stable",
                    },
                    {
                        "t_index": 2,
                        "months_ahead": 8,
                        "label": "+8mo",
                        "cells": [
                            {
                                "node_id": "n1",
                                "kind": "module",
                                "label": "lib/application.js",
                                "path": "lib/application.js",
                                "mass": 4.0,
                                "velocity": 1.0,
                                "momentum": 4.0,
                                "pressure": 1.81,
                            }
                        ],
                        "collisions": [{"a": "n1", "b": "n3", "reason": "schema", "intensity": 0.9}],
                        "narrative": "rising",
                        "narrative_kind": "rising_pressure",
                    },
                ],
                "ghosts": [
                    {
                        "intent": "split_module",
                        "title": "Split a god module",
                        "verdict": "warn",
                        "extensibility": 0.6,
                    }
                ],
                "costs": [{"month": 0, "compute": 1, "storage": 1, "egress": 1, "drivers": ["god_module"]}],
            },
        )
    if path == "/v1/missing":
        return httpx.Response(404, json={"detail": "nope"})
    return httpx.Response(404, json={"detail": "not found"})


def _client() -> Aether:
    return Aether("http://aether.test", transport=httpx.MockTransport(_router))


def test_health_and_ingest_wait():
    with _client() as client:
        assert client.health()["status"] == "ok"
        stages: list[str] = []
        result = client.ingest(url="https://github.com/expressjs/express", on_progress=lambda p, s: stages.append(s))
        assert result.universe_id == "abc"
        assert result.license == "MIT"
        assert "done" in stages


def test_forecast_helpers():
    with _client() as client:
        forecast = client.forecast("abc")
        assert isinstance(forecast, Forecast)
        hot = forecast.hottest(1, months=8)
        assert hot[0].label == "lib/application.js"
        assert hot[0].band == "high-pressure"
        assert forecast.storms(8)[0].reason == "schema"
        assert forecast.ghosts[0].verdict == "warn"
        now = forecast.frame(0)
        assert now is not None
        assert now.by_band()["calm"][0].label == "index.js"


def test_errors():
    with _client() as client:
        with pytest.raises(AetherHTTPError) as http_err:
            client._get("/v1/missing")
        assert http_err.value.status_code == 404
        with pytest.raises(AetherJobError, match="license denied"):
            client.wait_job("bad")
