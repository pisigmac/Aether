from __future__ import annotations


class AetherError(Exception):
    """Base SDK error."""


class AetherHTTPError(AetherError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


class AetherJobError(AetherError):
    def __init__(self, job_id: str, error: str) -> None:
        self.job_id = job_id
        self.error = error
        super().__init__(f"job {job_id} failed: {error}")
