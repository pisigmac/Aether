"""Ghost artifacts live in a temp worktree. The user's checkout is never written."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path


def open_sandbox(repo_path: str, dest_root: Path) -> Path:
    root = dest_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    dest = root / uuid.uuid4().hex
    repo = Path(repo_path).resolve() if repo_path else None
    if repo is not None and repo.exists() and _inside_git(repo):
        if dest.is_relative_to(repo):
            raise RuntimeError("sandbox must sit outside the checkout")
        created = subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach", str(dest), "HEAD"],
            capture_output=True,
            text=True,
        )
        if created.returncode == 0 and dest.is_dir() and not dest.is_relative_to(repo):
            return dest
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def write_ghost_artifact(sandbox: Path, intent: str) -> Path:
    if not intent or "/" in intent or "\\" in intent or intent.startswith("."):
        raise RuntimeError("refusing to write an unsafe ghost intent")
    root = sandbox.resolve()
    target = (root / "ghost" / f"{intent}.py").resolve()
    if not target.is_relative_to(root):
        raise RuntimeError("refusing to write outside the sandbox")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"# Aether ghost intent: {intent}\n"
        "# IR-only proposal. This file is not applied to the user checkout.\n"
    )
    return target


def _inside_git(path: Path) -> bool:
    probe = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return probe.returncode == 0 and probe.stdout.strip() == "true"
