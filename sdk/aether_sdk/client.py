from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

from aether_sdk.exceptions import AetherHTTPError, AetherJobError
from aether_sdk.models import (
    ChangeSet,
    Forecast,
    GraphSlice,
    IngestResult,
    JobAccepted,
    JobStatus,
    UniverseSummary,
)

ProgressFn = Callable[[int, str], None]


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    detail = response.text
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = str(payload.get("detail", payload))
    except ValueError:
        pass
    raise AetherHTTPError(response.status_code, detail)


class Aether:
    """Sync client for the Aether engine HTTP API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:18100",
        *,
        timeout: float = 60.0,
        headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=headers,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Aether:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def universes(self) -> list[UniverseSummary]:
        rows = self._get("/v1/universes")
        return [UniverseSummary.model_validate(row) for row in rows]

    def ingest(
        self,
        *,
        path: str = "",
        url: str = "",
        pr_ref: str = "",
        velocity: float | None = None,
        wait: bool = True,
        poll_interval: float = 0.35,
        on_progress: ProgressFn | None = None,
    ) -> IngestResult | JobAccepted:
        """Start an ingest job. By default waits until the forecast is ready."""
        body = {
            "path": path,
            "url": url,
            "pr_ref": pr_ref,
            "velocity_override": velocity,
        }
        accepted = JobAccepted.model_validate(self._post("/v1/jobs", body))
        if not wait:
            return accepted
        return self.wait_job(accepted.job_id, poll_interval=poll_interval, on_progress=on_progress)

    def ingest_now(
        self,
        *,
        path: str = "",
        url: str = "",
        pr_ref: str = "",
        velocity: float | None = None,
    ) -> IngestResult:
        """Blocking ingest on the request thread (small repos)."""
        return IngestResult.model_validate(
            self._post(
                "/v1/universes",
                {
                    "path": path,
                    "url": url,
                    "pr_ref": pr_ref,
                    "velocity_override": velocity,
                },
            )
        )

    def job(self, job_id: str) -> JobStatus:
        return JobStatus.model_validate(self._get(f"/v1/jobs/{job_id}"))

    def wait_job(
        self,
        job_id: str,
        *,
        poll_interval: float = 0.35,
        on_progress: ProgressFn | None = None,
    ) -> IngestResult:
        while True:
            status = self.job(job_id)
            if on_progress:
                on_progress(status.percent, status.stage)
            if status.failed:
                raise AetherJobError(job_id, status.error or "ingest failed")
            if status.done and status.result:
                return status.result
            time.sleep(poll_interval)

    def forecast(self, universe_id: str, horizon_months: int = 24) -> Forecast:
        return Forecast.model_validate(
            self._get(f"/v1/universes/{universe_id}/forecast", {"horizon_months": horizon_months})
        )

    def graph(self, universe_id: str, t: int = 0) -> GraphSlice:
        return GraphSlice.model_validate(self._get(f"/v1/universes/{universe_id}/graph", {"t": t}))

    def attach_changeset(self, universe_id: str, changeset: ChangeSet | dict[str, Any]) -> ChangeSet:
        payload = changeset.model_dump() if isinstance(changeset, ChangeSet) else changeset
        return ChangeSet.model_validate(self._post(f"/v1/universes/{universe_id}/changesets", payload))

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = self._client.get(path, params=params)
        _raise_for_status(response)
        return response.json()

    def _post(self, path: str, body: dict[str, Any]) -> Any:
        response = self._client.post(path, json=body)
        _raise_for_status(response)
        return response.json()


class AsyncAether:
    """Async client for the Aether engine HTTP API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:18100",
        *,
        timeout: float = 60.0,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=headers,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncAether:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def health(self) -> dict[str, Any]:
        return await self._get("/health")

    async def universes(self) -> list[UniverseSummary]:
        rows = await self._get("/v1/universes")
        return [UniverseSummary.model_validate(row) for row in rows]

    async def ingest(
        self,
        *,
        path: str = "",
        url: str = "",
        pr_ref: str = "",
        velocity: float | None = None,
        wait: bool = True,
        poll_interval: float = 0.35,
        on_progress: ProgressFn | None = None,
    ) -> IngestResult | JobAccepted:
        body = {
            "path": path,
            "url": url,
            "pr_ref": pr_ref,
            "velocity_override": velocity,
        }
        accepted = JobAccepted.model_validate(await self._post("/v1/jobs", body))
        if not wait:
            return accepted
        return await self.wait_job(accepted.job_id, poll_interval=poll_interval, on_progress=on_progress)

    async def ingest_now(
        self,
        *,
        path: str = "",
        url: str = "",
        pr_ref: str = "",
        velocity: float | None = None,
    ) -> IngestResult:
        return IngestResult.model_validate(
            await self._post(
                "/v1/universes",
                {
                    "path": path,
                    "url": url,
                    "pr_ref": pr_ref,
                    "velocity_override": velocity,
                },
            )
        )

    async def job(self, job_id: str) -> JobStatus:
        return JobStatus.model_validate(await self._get(f"/v1/jobs/{job_id}"))

    async def wait_job(
        self,
        job_id: str,
        *,
        poll_interval: float = 0.35,
        on_progress: ProgressFn | None = None,
    ) -> IngestResult:
        import asyncio

        while True:
            status = await self.job(job_id)
            if on_progress:
                on_progress(status.percent, status.stage)
            if status.failed:
                raise AetherJobError(job_id, status.error or "ingest failed")
            if status.done and status.result:
                return status.result
            await asyncio.sleep(poll_interval)

    async def forecast(self, universe_id: str, horizon_months: int = 24) -> Forecast:
        return Forecast.model_validate(
            await self._get(f"/v1/universes/{universe_id}/forecast", {"horizon_months": horizon_months})
        )

    async def graph(self, universe_id: str, t: int = 0) -> GraphSlice:
        return GraphSlice.model_validate(await self._get(f"/v1/universes/{universe_id}/graph", {"t": t}))

    async def attach_changeset(self, universe_id: str, changeset: ChangeSet | dict[str, Any]) -> ChangeSet:
        payload = changeset.model_dump() if isinstance(changeset, ChangeSet) else changeset
        return ChangeSet.model_validate(await self._post(f"/v1/universes/{universe_id}/changesets", payload))

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._client.get(path, params=params)
        _raise_for_status(response)
        return response.json()

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        response = await self._client.post(path, json=body)
        _raise_for_status(response)
        return response.json()
