from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aether.config import settings


@dataclass(frozen=True)
class SampleCommit:
    sha: str
    authored_at: str


def _run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def is_git_repo(root: Path) -> bool:
    try:
        inside = _run_git(root, "rev-parse", "--is-inside-work-tree").strip()
        if inside != "true":
            return False
        toplevel = Path(_run_git(root, "rev-parse", "--show-toplevel").strip()).resolve()
        return toplevel == root.resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def list_source_paths(root: Path, sha: str | None = None) -> list[str]:
    if sha and is_git_repo(root):
        out = _run_git(root, "ls-tree", "-r", "--name-only", sha)
        return [line for line in out.splitlines() if line]
    paths: list[str] = []
    ignore = {
        ".git", "node_modules", ".venv", "venv", "__pycache__",
        ".next", "dist", "build", ".mypy_cache", ".pytest_cache", "data",
    }
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in ignore for part in rel.parts):
            continue
        paths.append(str(rel).replace("\\", "/"))
    return paths


def show_file(root: Path, rel_path: str, sha: str | None = None) -> str:
    if sha and is_git_repo(root):
        found = batch_show_files(root, sha, [rel_path])
        return found.get(rel_path, "")
    path = root / rel_path
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def batch_show_files(root: Path, sha: str | None, paths: list[str]) -> dict[str, str]:
    """Read many blobs in one git process. Missing paths are omitted."""
    if not paths:
        return {}
    if sha and is_git_repo(root):
        return _cat_file_batch(root, sha, paths)
    found: dict[str, str] = {}
    for rel in paths:
        path = root / rel
        if path.is_file():
            found[rel] = path.read_text(encoding="utf-8", errors="ignore")
    return found


def diff_paths(root: Path, old_sha: str, new_sha: str) -> tuple[list[str], list[str]]:
    """Net (touched, removed) paths between two commits, renames counted as delete plus add."""
    out = _run_git(root, "diff", "--name-status", "--no-renames", "-z", old_sha, new_sha)
    touched: list[str] = []
    removed: list[str] = []
    parts = out.split("\0")
    i = 0
    while i + 1 < len(parts):
        status, path = parts[i], parts[i + 1]
        i += 2
        if not path:
            continue
        if status.startswith("D"):
            removed.append(path)
        else:
            touched.append(path)
    return touched, removed


def _cat_file_batch(root: Path, sha: str, paths: list[str]) -> dict[str, str]:
    proc = subprocess.Popen(
        ["git", "-C", str(root), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None

    def _write() -> None:
        assert proc.stdin is not None
        proc.stdin.write("".join(f"{sha}:{path}\n" for path in paths).encode())
        proc.stdin.close()

    writer = threading.Thread(target=_write, daemon=True)
    writer.start()
    found: dict[str, str] = {}
    for path in paths:
        header = proc.stdout.readline()
        if not header:
            break
        text = header.decode("utf-8", "replace").strip()
        if text.endswith(" missing"):
            continue
        bits = text.split()
        if len(bits) < 3:
            continue
        size = int(bits[-1])
        blob = proc.stdout.read(size)
        proc.stdout.read(1)
        if bits[-2] != "blob":
            continue
        found[path] = blob.decode("utf-8", "replace")
    writer.join()
    proc.wait()
    return found


def commits_per_week(root: Path) -> float:
    if not is_git_repo(root):
        return 1.0
    try:
        out = _run_git(root, "log", "--first-parent", "--format=%cI")
    except subprocess.CalledProcessError:
        return 1.0
    stamps = [line.strip() for line in out.splitlines() if line.strip()]
    if len(stamps) < 2:
        return float(max(len(stamps), 1))
    newest = _parse_iso(stamps[0])
    oldest = _parse_iso(stamps[-1])
    weeks = max((newest - oldest).total_seconds() / (7 * 86400), 1.0)
    return round(len(stamps) / weeks, 3)


def sample_commits(
    root: Path,
    max_samples: int | None = None,
    lookback_months: int | None = None,
) -> list[SampleCommit]:
    cap = max_samples or settings.max_samples
    months = lookback_months or settings.lookback_months
    if not is_git_repo(root):
        now = datetime.now(timezone.utc).isoformat()
        return [SampleCommit(sha="WORKING_TREE", authored_at=now)]

    out = _run_git(root, "log", "--first-parent", "--format=%H %cI")
    rows: list[SampleCommit] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, stamp = line.split(" ", 1)
        authored = _parse_iso(stamp.strip())
        if authored < cutoff and rows:
            break
        rows.append(SampleCommit(sha=sha, authored_at=authored.isoformat()))

    if not rows:
        sha = _run_git(root, "rev-parse", "HEAD").strip()
        stamp = _run_git(root, "log", "-1", "--format=%cI").strip()
        return [SampleCommit(sha=sha, authored_at=stamp)]

    # newest-first from git log; keep HEAD, then evenly sample older history
    if len(rows) <= cap:
        return list(reversed(rows))
    if cap <= 1:
        return [rows[0]]

    head, rest = rows[0], rows[1:]
    step = max(len(rest) / (cap - 1), 1.0)
    picked = [head]
    idx = 0.0
    while len(picked) < cap and int(idx) < len(rest):
        candidate = rest[int(idx)]
        if candidate.sha != picked[-1].sha:
            picked.append(candidate)
        idx += step
    return list(reversed(picked))


def _parse_iso(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
