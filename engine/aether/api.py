from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aether.acquisition.git_ingest import IngestRequest
from aether.config import settings
from aether.gates.guardloop import GuardLoopClient, GuardLoopError, GuardLoopGate
from aether.gates.tracelens import TraceLensClient, TraceLensError, TraceLensTracer
from aether.ir.models import ChangeSet, ForecastBundle, GhostResult
from aether.jobs import IngestCancelled, store as job_store
from aether.parsers.ids import stable_id
from aether.physics.butterfly import apply_changeset
from aether.physics.forecast import build_forecast, graph_slice
from aether.physics.ghosts import AgentGhostRunner, run_ghost_lab
from aether.physics.predictor import predictor_for_mode, resolve_predictor
from aether.pipeline import attach_changeset, build_universe
from aether.storage.db import AetherDB

db: AetherDB | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global db
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db = AetherDB(settings.data_dir / "aether.db")
    yield


app = FastAPI(title="Aether Engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins
    + ["http://127.0.0.1:3000", "http://localhost:13100", "http://127.0.0.1:13100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestBody(BaseModel):
    path: str = ""
    url: str = ""
    pr_ref: str = ""
    velocity_override: float | None = None


class IngestResponse(BaseModel):
    universe_id: str
    repo_path: str
    license: str
    snapshots: int
    velocity_commits_per_week: float
    warnings: list[str] = Field(default_factory=list)


class JobAccepted(BaseModel):
    job_id: str
    status: str
    percent: int
    stage: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    percent: int
    stage: str
    error: str = ""
    result: IngestResponse | None = None
    created_at: str = ""
    label: str = ""


def _db() -> AetherDB:
    if db is None:
        raise HTTPException(503, "database not ready")
    return db


def _to_ingest(universe, warnings: list[str]) -> IngestResponse:
    return IngestResponse(
        universe_id=universe.id,
        repo_path=universe.repo_path,
        license=universe.license,
        snapshots=len(universe.snapshots),
        velocity_commits_per_week=universe.velocity_commits_per_week,
        warnings=warnings,
    )


def _run_job(job_id: str, body: IngestBody) -> None:
    job_store.update(job_id, 2, "Starting ingest")

    def on_progress(percent: int, stage: str) -> None:
        if job_store.is_cancelled(job_id):
            raise IngestCancelled()
        job_store.update(job_id, percent, stage)

    try:
        universe, warnings = build_universe(
            IngestRequest(
                path=body.path,
                url=body.url,
                pr_ref=body.pr_ref,
                velocity_override=body.velocity_override,
            ),
            _db(),
            on_progress=on_progress,
        )
        if not job_store.is_cancelled(job_id):
            job_store.finish(job_id, _to_ingest(universe, warnings).model_dump())
    except IngestCancelled:
        job_store.cancel(job_id)
    except Exception as exc:
        job_store.fail(job_id, str(exc))


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "aether-engine",
        "data_dir": str(settings.data_dir),
    }


@app.get("/v1/universes")
def list_universes() -> list[dict]:
    return _db().list_universes()


@app.post("/v1/universes", response_model=IngestResponse)
def create_universe(body: IngestBody) -> IngestResponse:
    try:
        universe, warnings = build_universe(
            IngestRequest(
                path=body.path,
                url=body.url,
                pr_ref=body.pr_ref,
                velocity_override=body.velocity_override,
            ),
            _db(),
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _to_ingest(universe, warnings)


def _job_status(job) -> JobStatus:
    result = IngestResponse.model_validate(job.result) if job.result else None
    return JobStatus(
        job_id=job.id,
        status=job.status,
        percent=job.percent,
        stage=job.stage,
        error=job.error,
        result=result,
        created_at=job.created_at,
        label=job.label,
    )


@app.post("/v1/jobs", response_model=JobAccepted)
def start_ingest_job(body: IngestBody) -> JobAccepted:
    job = job_store.create(label=body.path or body.url or "")
    threading.Thread(target=_run_job, args=(job.id, body), daemon=True).start()
    return JobAccepted(job_id=job.id, status="queued", percent=0, stage="queued")


@app.get("/v1/jobs", response_model=list[JobStatus])
def list_ingest_jobs(limit: int = 20) -> list[JobStatus]:
    return [_job_status(job) for job in job_store.list(limit)]


@app.post("/v1/jobs/{job_id}/cancel", response_model=JobStatus)
def cancel_ingest_job(job_id: str) -> JobStatus:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    job_store.cancel(job_id)
    updated = job_store.get(job_id)
    assert updated is not None
    return _job_status(updated)


@app.get("/v1/jobs/{job_id}", response_model=JobStatus)
def get_ingest_job(job_id: str) -> JobStatus:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return _job_status(job)


@app.post("/v1/universes/{universe_id}/changesets", response_model=ChangeSet)
def create_changeset(universe_id: str, body: ChangeSet) -> ChangeSet:
    body.universe_id = universe_id
    if not body.id:
        body.id = stable_id("changeset", universe_id, body.label)
    try:
        return attach_changeset(_db(), universe_id, body)
    except KeyError:
        raise HTTPException(404, "universe not found") from None


@app.get("/v1/predictor")
def get_predictor() -> dict:
    predictor = resolve_predictor(settings.model_path)
    return {
        "name": predictor.name,
        "model_id": predictor.model_id,
        "training_records": predictor.training_records,
        "learned_available": predictor.name == "learned",
    }


@app.get("/v1/universes/{universe_id}/forecast", response_model=ForecastBundle)
def get_forecast(universe_id: str, horizon_months: int = 24, mode: str = "auto") -> ForecastBundle:
    store = _db()
    universe = store.get_universe(universe_id)
    if not universe:
        raise HTTPException(404, "universe not found")
    existing = store.get_forecast(universe_id)
    changesets = store.list_changesets(universe_id)
    changeset = changesets[-1] if changesets else None
    normalized = (mode or "auto").strip().lower()
    if normalized == "auto" and existing and existing.horizon_months == horizon_months:
        return existing
    try:
        predictor = None if normalized == "auto" else predictor_for_mode(normalized, settings.model_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(409, str(exc)) from exc
    bundle = build_forecast(
        universe,
        horizon_months=horizon_months,
        changeset=changeset,
        predictor=predictor,
    )
    if normalized == "auto":
        store.upsert_forecast(bundle)
    return bundle


@app.post("/v1/universes/{universe_id}/ghosts", response_model=list[GhostResult])
def run_guarded_ghosts(
    universe_id: str,
    budget: int = Query(default=50, ge=1, le=500),
    x_guardloop_key: Annotated[str | None, Header()] = None,
    x_tracelens_key: Annotated[str | None, Header()] = None,
) -> list[GhostResult]:
    if not settings.guardloop_url:
        raise HTTPException(503, "GuardLoop URL is not configured")
    if settings.tracelens_url and not x_tracelens_key:
        raise HTTPException(401, "TraceLens token is required")
    store = _db()
    universe = store.get_universe(universe_id)
    if not universe or not universe.snapshots:
        raise HTTPException(404, "universe not found")
    changesets = store.list_changesets(universe_id)
    changeset = changesets[-1] if changesets else None
    projected = apply_changeset(universe.snapshots[-1], changeset)
    gate = GuardLoopGate(GuardLoopClient(settings.guardloop_url, api_key=x_guardloop_key or ""))
    tracer = None
    if settings.tracelens_url:
        tracer = TraceLensTracer(
            TraceLensClient(settings.tracelens_url, api_key=x_tracelens_key or ""),
            dashboard_url=settings.tracelens_dashboard_url,
        )
    runner = AgentGhostRunner(
        gate=gate,
        budget=budget,
        session_name=f"aether-ghost:{universe_id}",
        tracer=tracer,
    )
    try:
        return run_ghost_lab(projected, runner)
    except (GuardLoopError, TraceLensError) as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/v1/universes/{universe_id}/graph")
def get_graph(universe_id: str, t: int = 0) -> dict:
    universe = _db().get_universe(universe_id)
    if not universe or not universe.snapshots:
        raise HTTPException(404, "universe not found")
    idx = min(max(t, 0), len(universe.snapshots) - 1)
    return graph_slice(universe.snapshots[idx])
