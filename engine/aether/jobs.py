from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

Status = Literal["queued", "running", "done", "error"]
ProgressFn = Callable[[int, str], None]


@dataclass
class Job:
    id: str
    status: Status = "queued"
    percent: int = 0
    stage: str = "queued"
    error: str = ""
    result: dict[str, Any] = field(default_factory=dict)


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}

    def create(self) -> Job:
        job = Job(id=uuid.uuid4().hex[:12])
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return Job(
                id=job.id,
                status=job.status,
                percent=job.percent,
                stage=job.stage,
                error=job.error,
                result=dict(job.result),
            )

    def update(self, job_id: str, percent: int, stage: str, status: Status = "running") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = status
            job.percent = max(0, min(100, percent))
            job.stage = stage

    def finish(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "done"
            job.percent = 100
            job.stage = "done"
            job.result = result

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "error"
            job.stage = "failed"
            job.error = error


store = JobStore()
