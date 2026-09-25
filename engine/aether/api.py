from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aether.acquisition.git_ingest import IngestRequest
from aether.auth.deps import require_principal
from aether.auth.ownership import same_org
from aether.auth.principal import Principal
from aether.auth.routes import router as auth_router
from aether.config import settings
from aether.gates.guardloop import GuardLoopClient, GuardLoopError, GuardLoopGate
from aether.gates.tracelens import TraceLensClient, TraceLensError, TraceLensTracer
from aether.ir.models import ChangeSet, ForecastBundle, GhostRun
from aether.jobs import JobStore
from aether.live import blank, forecast_reading, job_targets_repo, pick_universe_id
from aether.worker import spawn as spawn_worker
from aether.parsers.ids import stable_id
from aether.physics.butterfly import apply_changeset
from aether.physics.forecast import build_forecast, graph_slice
from aether.physics.ghosts import (
    DEFAULT_GHOST_PARALLEL,
    MAX_GHOST_PARALLEL,
    AgentGhostRunner,
    disclose_parallel,
    run_ghost_lab,
)
from aether.physics.sandbox import open_sandbox
from aether.physics.predictor import predictor_for_mode, resolve_predictor
from aether.pipeline import attach_changeset, build_universe
from aether.storage.db import AetherDB, open_database

db: AetherDB | None = None
job_store: JobStore | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global db, job_store
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db_path = settings.data_dir / "aether.db"
    db = open_database(db_path)
    job_store = JobStore(db_path)
    worker = None
    if os.environ.get("AETHER_INGEST_WORKER", "1") != "0":
        worker = spawn_worker()
    try:
        yield
    finally:
        if worker is not None:
            worker.terminate()
            try:
                worker.wait(timeout=5)
            except Exception:
                worker.kill()


app = FastAPI(title="Aether Engine", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)
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
    sample_policy: str = "even"
    sample_every: int = Field(default=1, ge=1)


class IngestResponse(BaseModel):
    universe_id: str
    repo_path: str
    license: str
    snapshots: int
    velocity_commits_per_week: float
    sample_policy: str = "even"
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


def _ingest_request(body: IngestBody) -> IngestRequest:
    return IngestRequest(
        path=body.path,
        url=body.url,
        pr_ref=body.pr_ref,
        velocity_override=body.velocity_override,
        sample_policy=body.sample_policy,
        sample_every=body.sample_every,
    )


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
        sample_policy=universe.sample_policy,
        warnings=warnings,
    )


def _owned_universe(universe_id: str, principal: Principal | None):
    universe = _db().get_universe(universe_id)
    if universe is None or not same_org(principal, universe.org_id):
        raise HTTPException(404, "universe not found")
    return universe


def _summary(universe) -> dict:
    return {
        "id": universe.id,
        "repo_path": universe.repo_path,
        "license": universe.license,
        "velocity": universe.velocity_commits_per_week,
        "org_id": universe.org_id,
    }


def _actor(principal: Principal | None) -> str:
    if principal is None:
        return "local"
    return principal.email or principal.sub or "local"


def _jobs() -> JobStore:
    if job_store is None:
        raise HTTPException(503, "jobs not ready")
    return job_store


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "aether-engine",
        "data_dir": str(settings.data_dir),
        "database": "postgres" if settings.database_url else "sqlite",
    }


@app.get("/v1/universes")
def list_universes(principal: Principal | None = Depends(require_principal)) -> list[dict]:
    org_id = None if principal is None else principal.org_id
    return _db().list_universes(org_id)


@app.get("/v1/universes/{universe_id}")
def get_universe(
    universe_id: str,
    principal: Principal | None = Depends(require_principal),
) -> dict:
    return _summary(_owned_universe(universe_id, principal))


@app.delete("/v1/universes/{universe_id}", status_code=204)
def delete_universe(
    universe_id: str,
    principal: Principal | None = Depends(require_principal),
) -> Response:
    _owned_universe(universe_id, principal)
    _db().delete_universe(universe_id)
    return Response(status_code=204)


@app.post("/v1/universes", response_model=IngestResponse)
def create_universe(
    body: IngestBody,
    _principal: Principal | None = Depends(require_principal),
) -> IngestResponse:
    try:
        universe, warnings = build_universe(
            _ingest_request(body),
            _db(),
            org_id=_principal.org_id if _principal else "",
            actor=_actor(_principal),
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


def _owned_job(job_id: str, principal: Principal | None):
    job = _jobs().get(job_id)
    if job is None or not same_org(principal, job.org_id):
        raise HTTPException(404, "job not found")
    return job


@app.post("/v1/jobs", response_model=JobAccepted)
def start_ingest_job(
    body: IngestBody,
    _principal: Principal | None = Depends(require_principal),
) -> JobAccepted:
    payload = body.model_dump()
    payload["_actor"] = _actor(_principal)
    job = _jobs().create(
        label=body.path or body.url or "",
        org_id=_principal.org_id if _principal else "",
        request=payload,
    )
    return JobAccepted(job_id=job.id, status="queued", percent=0, stage="queued")


@app.get("/v1/audit")
def list_audit(
    limit: int = 50,
    principal: Principal | None = Depends(require_principal),
) -> list[dict]:
    org_id = None if principal is None else principal.org_id
    return _db().list_audit(org_id=org_id, limit=limit)


@app.get("/v1/live")
def live_reading(
    repo: str = "",
    principal: Principal | None = Depends(require_principal),
) -> dict:
    """One cell for the desktop bar. A running ingest hides pressure."""
    if not repo.strip():
        return blank("empty")
    org_id = None if principal is None else principal.org_id
    rows = [(row["id"], row["repo_path"]) for row in _db().list_universes(org_id)]
    jobs = _jobs().list(limit=20, org_id=org_id)

    def targets(job) -> bool:
        result_path = ""
        if job.result:
            result_path = str(job.result.get("repo_path") or "")
        return job_targets_repo(
            job.label,
            str(job.request.get("path") or ""),
            result_path,
            repo,
        )

    active = next((job for job in jobs if job.status in ("queued", "running") and targets(job)), None)
    if active is not None:
        return blank("ingesting", repo, percent=active.percent, stage=active.stage or "Queued")
    universe_id = pick_universe_id(rows, repo)
    if not universe_id:
        failed = next((job for job in jobs if job.status == "error" and targets(job)), None)
        if failed is not None:
            return blank("error", repo, error=failed.error or failed.stage, stage=failed.stage)
        return blank("missing", repo)
    bundle = get_forecast(universe_id, principal=principal)
    return forecast_reading(bundle)


@app.get("/v1/jobs", response_model=list[JobStatus])
def list_ingest_jobs(
    limit: int = 20,
    principal: Principal | None = Depends(require_principal),
) -> list[JobStatus]:
    org_id = None if principal is None else principal.org_id
    return [_job_status(job) for job in _jobs().list(limit, org_id=org_id)]


@app.post("/v1/jobs/{job_id}/cancel", response_model=JobStatus)
def cancel_ingest_job(
    job_id: str,
    _principal: Principal | None = Depends(require_principal),
) -> JobStatus:
    _owned_job(job_id, _principal)
    _jobs().cancel(job_id)
    updated = _jobs().get(job_id)
    assert updated is not None
    return _job_status(updated)


@app.get("/v1/jobs/{job_id}", response_model=JobStatus)
def get_ingest_job(
    job_id: str,
    principal: Principal | None = Depends(require_principal),
) -> JobStatus:
    return _job_status(_owned_job(job_id, principal))


@app.post("/v1/universes/{universe_id}/changesets", response_model=ChangeSet)
def create_changeset(
    universe_id: str,
    body: ChangeSet,
    _principal: Principal | None = Depends(require_principal),
) -> ChangeSet:
    _owned_universe(universe_id, _principal)
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
def get_forecast(
    universe_id: str,
    horizon_months: int = 24,
    mode: str = "auto",
    principal: Principal | None = Depends(require_principal),
) -> ForecastBundle:
    store = _db()
    universe = _owned_universe(universe_id, principal)
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


@app.post("/v1/universes/{universe_id}/ghosts", response_model=GhostRun)
def run_guarded_ghosts(
    universe_id: str,
    budget: int = Query(default=50, ge=1, le=500),
    parallel: int = Query(default=DEFAULT_GHOST_PARALLEL, ge=1, le=MAX_GHOST_PARALLEL),
    x_guardloop_key: Annotated[str | None, Header()] = None,
    x_tracelens_key: Annotated[str | None, Header()] = None,
    _principal: Principal | None = Depends(require_principal),
) -> GhostRun:
    universe = _owned_universe(universe_id, _principal)
    if not settings.guardloop_url:
        raise HTTPException(503, "GuardLoop URL is not configured")
    if settings.tracelens_url and not x_tracelens_key:
        raise HTTPException(401, "TraceLens token is required")
    store = _db()
    if not universe.snapshots:
        raise HTTPException(404, "universe not found")
    changesets = store.list_changesets(universe_id)
    changeset = changesets[-1] if changesets else None
    projected = apply_changeset(universe.snapshots[-1], changeset)
    sandbox = open_sandbox(universe.repo_path, settings.data_dir / "ghost-sandboxes" / universe_id)
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
        sandbox=sandbox,
    )
    started = time.perf_counter()
    try:
        ghosts = run_ghost_lab(projected, runner, parallel=parallel)
    except (GuardLoopError, TraceLensError, ValueError) as exc:
        raise HTTPException(502, str(exc)) from exc
    return GhostRun(
        parallel=parallel,
        duration_ms=int((time.perf_counter() - started) * 1000),
        disclosure=disclose_parallel(parallel),
        sandbox=str(sandbox),
        ghosts=ghosts,
    )


@app.get("/v1/universes/{universe_id}/graph")
def get_graph(
    universe_id: str,
    t: int = 0,
    principal: Principal | None = Depends(require_principal),
) -> dict:
    universe = _owned_universe(universe_id, principal)
    if not universe.snapshots:
        raise HTTPException(404, "universe not found")
    idx = min(max(t, 0), len(universe.snapshots) - 1)
    return graph_slice(universe.snapshots[idx])
