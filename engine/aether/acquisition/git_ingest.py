from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from aether.acquisition.licenses import detect_license, license_allowed
from aether.acquisition.sampler import (
    SampleCommit,
    commits_per_week,
    is_git_repo,
    sample_commits,
)
from aether.config import settings
from aether.jobs import ProgressFn


@dataclass
class IngestRequest:
    path: str = ""
    url: str = ""
    pr_ref: str = ""
    velocity_override: float | None = None


@dataclass
class IngestedRepo:
    root: Path
    license: str
    samples: list[SampleCommit]
    velocity: float
    warnings: list[str]


def ingest_repo(
    req: IngestRequest,
    data_dir: Path | None = None,
    on_progress: ProgressFn | None = None,
) -> IngestedRepo:
    warnings: list[str] = []
    report = on_progress or (lambda _pct, _stage: None)
    report(4, "Resolving repository")
    root = _resolve_root(req, data_dir or settings.data_dir, on_progress)
    report(14, "Checking license")
    license_id = detect_license(root)
    if license_id == "UNKNOWN":
        warnings.append("No recognized LICENSE file; proceeding as local working tree.")
    elif not license_allowed(license_id):
        raise PermissionError(
            f"License {license_id} is outside the allowlist "
            f"({', '.join(sorted(settings.allowed_licenses))})."
        )

    report(18, "Sampling git history")
    samples = sample_commits(root)
    velocity = req.velocity_override if req.velocity_override else commits_per_week(root)
    if velocity <= 0.2:
        velocity = 1.0
        warnings.append("Inferred velocity was too low; defaulting to 1 commit/week.")
    report(22, f"Sampled {len(samples)} commits")
    return IngestedRepo(
        root=root,
        license=license_id,
        samples=samples,
        velocity=velocity,
        warnings=warnings,
    )


def _resolve_root(
    req: IngestRequest,
    data_dir: Path,
    on_progress: ProgressFn | None = None,
) -> Path:
    if req.path:
        raw = Path(req.path).expanduser()
        candidates = [raw] if raw.is_absolute() else [Path.cwd() / raw, Path.cwd().parent / raw]
        for cand in candidates:
            if cand.exists():
                return cand.resolve()
        raise FileNotFoundError(f"Path does not exist: {raw}")
    if req.url:
        return _clone_url(req.url, data_dir, on_progress)
    raise ValueError("Provide a local path or git URL.")


def _clone_url(url: str, data_dir: Path, on_progress: ProgressFn | None = None) -> Path:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "git"}:
        raise ValueError("Only https/git clone URLs are accepted.")
    if parsed.scheme == "https" and parsed.hostname not in {
        "github.com",
        "gitlab.com",
        "bitbucket.org",
        "codeberg.org",
    }:
        raise ValueError("Remote clone is limited to known public forges.")

    data_dir.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha1(url.encode()).hexdigest()[:12]
    dest = data_dir / "clones" / name
    report = on_progress or (lambda _pct, _stage: None)
    if dest.exists() and is_git_repo(dest):
        report(8, "Fetching latest commits")
        subprocess.run(["git", "-C", str(dest), "fetch", "--all"], check=False, capture_output=True)
        report(12, "Fetch complete")
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    report(8, "Cloning repository")
    subprocess.run(["git", "clone", "--filter=blob:none", url, str(dest)], check=True)
    report(12, "Clone complete")
    return dest
