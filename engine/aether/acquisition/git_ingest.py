from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from aether.acquisition.licenses import LicenseRejected, detect_license, license_allowed
from aether.acquisition.sampler import (
    SampleCommit,
    commits_per_week,
    is_git_repo,
    list_source_paths,
    sample_commits,
)
from aether.config import settings
from aether.jobs import IngestCancelled, ProgressFn

_GIT_PCT = re.compile(
    r"(?:Receiving objects|Resolving deltas|Updating files|Counting objects):\s+(\d+)%"
)


@dataclass
class IngestRequest:
    path: str = ""
    url: str = ""
    pr_ref: str = ""
    velocity_override: float | None = None
    lookback_months: int | None = None
    max_samples: int | None = None
    sample_policy: str = "even"
    sample_every: int = 1


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
    report(17, "Checking license")
    license_id = detect_license(root)
    if license_id == "UNKNOWN":
        warnings.append("No recognized LICENSE file; proceeding as local working tree.")
    elif not license_allowed(license_id):
        raise LicenseRejected(license_id)

    report(18, "Sampling git history")
    snap_cap = req.max_samples or settings.max_samples
    if settings.max_snapshots > 0:
        snap_cap = min(snap_cap, settings.max_snapshots)
    samples = sample_commits(
        root,
        max_samples=snap_cap,
        lookback_months=req.lookback_months,
        policy=req.sample_policy or "even",
        every=req.sample_every,
        warnings=warnings,
    )
    _enforce_caps(root, samples, warnings)
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
        _run_git_with_progress(
            ["git", "-C", str(dest), "fetch", "--all", "--progress"],
            report,
            8,
            16,
            check=False,
            stage="Fetching latest commits",
        )
        report(16, "Fetch complete")
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    report(8, "Cloning repository")
    try:
        _run_git_with_progress(
            ["git", "clone", "--filter=blob:none", "--progress", url, str(dest)],
            report,
            8,
            16,
            stage="Cloning repository",
        )
    except IngestCancelled:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    report(16, "Clone complete")
    return dest


def clone_percent(line: str, lo: int = 8, hi: int = 16) -> int | None:
    """Map a git --progress line onto the clone slice of the ingest bar."""
    match = _GIT_PCT.search(line)
    if not match:
        return None
    return lo + int((hi - lo) * (int(match.group(1)) / 100))


def _run_git_with_progress(
    args: list[str],
    report: ProgressFn,
    lo: int,
    hi: int,
    check: bool = True,
    stage: str = "Cloning repository",
) -> None:
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    err_tail: list[str] = []
    try:
        assert proc.stderr is not None
        for raw in proc.stderr:
            err_tail.append(raw)
            err_tail = err_tail[-20:]
            for part in raw.replace("\r", "\n").splitlines():
                pct = clone_percent(part, lo, hi)
                if pct is not None:
                    report(pct, stage)
        code = proc.wait()
    except IngestCancelled:
        if proc.poll() is None:
            proc.kill()
        raise
    if code != 0 and check:
        raise subprocess.CalledProcessError(code, args, stderr="".join(err_tail))


def _enforce_caps(root: Path, samples: list[SampleCommit], warnings: list[str]) -> None:
    files = list_source_paths(root)
    if settings.max_source_files > 0 and len(files) > settings.max_source_files:
        raise ValueError(
            f"Repository has {len(files)} source files, above the cap of {settings.max_source_files}."
        )
    size = _tree_bytes(root)
    if settings.max_clone_bytes > 0 and size > settings.max_clone_bytes:
        raise ValueError(
            f"Repository is {size} bytes, above the cap of {settings.max_clone_bytes}."
        )
    if is_git_repo(root) and settings.max_snapshots > 0:
        try:
            count = int(
                subprocess.run(
                    ["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                or "0"
            )
        except (subprocess.CalledProcessError, ValueError):
            count = 0
        if count > len(samples):
            warnings.append(
                f"History has {count} commits; sampling {len(samples)} (cap {settings.max_snapshots})."
            )


def _tree_bytes(root: Path) -> int:
    ignore = {
        ".git", "node_modules", ".venv", "venv", "__pycache__",
        ".next", "dist", "build", ".mypy_cache", ".pytest_cache", "data",
    }
    total = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignore for part in path.relative_to(root).parts):
            continue
        total += path.stat().st_size
    return total
