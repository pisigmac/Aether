import os
import subprocess
from pathlib import Path

import pytest

from aether.acquisition.adapters import GhArchiveAdapter, SoftwareHeritageAdapter
from aether.acquisition.licenses import detect_license, license_allowed
from aether.acquisition.sampler import sample_commits
from aether.ir.models import Universe


def test_license_allowlist(tmp_path: Path):
    (tmp_path / "LICENSE").write_text("MIT License\nPermission is hereby granted, free of charge", encoding="utf-8")
    assert detect_license(tmp_path) == "MIT"
    assert license_allowed("MIT")
    assert not license_allowed("GPL-3.0")


def test_sample_working_tree(tmp_path: Path):
    samples = sample_commits(tmp_path)
    assert len(samples) == 1
    assert samples[0].sha == "WORKING_TREE"


def _git(repo: Path, *args: str, when: str | None = None) -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Aether"
    env["GIT_AUTHOR_EMAIL"] = "aether@example.com"
    env["GIT_COMMITTER_NAME"] = "Aether"
    env["GIT_COMMITTER_EMAIL"] = "aether@example.com"
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _history(repo: Path) -> list[str]:
    _git(repo, "init")
    shas: list[str] = []
    for name, when in (
        ("a", "2026-01-05T12:00:00+00:00"),
        ("b", "2026-01-06T12:00:00+00:00"),
        ("c", "2026-01-12T12:00:00+00:00"),
        ("d", "2026-01-20T12:00:00+00:00"),
    ):
        (repo / "note.txt").write_text(name + "\n", encoding="utf-8")
        _git(repo, "add", "note.txt")
        _git(repo, "commit", "-m", name, when=when)
        shas.append(_git(repo, "rev-parse", "HEAD"))
    return shas


def test_weekly_keeps_the_newest_commit_in_each_week(tmp_path: Path):
    shas = _history(tmp_path)
    samples = sample_commits(tmp_path, policy="weekly", max_samples=20)
    assert [item.sha for item in samples] == [shas[1], shas[2], shas[3]]


def test_every_nth_keeps_head(tmp_path: Path):
    shas = _history(tmp_path)
    samples = sample_commits(tmp_path, policy="every", every=2, max_samples=20)
    assert [item.sha for item in samples] == [shas[1], shas[3]]


def test_tag_only_skips_untagged_head(tmp_path: Path):
    shas = _history(tmp_path)
    _git(tmp_path, "tag", "v1", shas[2])
    warnings: list[str] = []
    samples = sample_commits(tmp_path, policy="tag", max_samples=20, warnings=warnings)
    assert [item.sha for item in samples] == [shas[2]]
    assert warnings == []


def test_tag_policy_without_tags_samples_head(tmp_path: Path):
    shas = _history(tmp_path)
    warnings: list[str] = []
    samples = sample_commits(tmp_path, policy="tag", max_samples=20, warnings=warnings)
    assert [item.sha for item in samples] == [shas[-1]]
    assert warnings


def test_unknown_sample_policy_is_rejected(tmp_path: Path):
    with pytest.raises(ValueError, match="sample_policy"):
        sample_commits(tmp_path, policy="daily")


def test_old_universe_payload_defaults_the_sample_policy():
    universe = Universe.model_validate({"id": "u", "repo_path": "/tmp/x"})
    assert universe.sample_policy == "even"
    assert universe.sample_every == 1


def test_adapters_document_legal_queries():
    assert "PushEvent" in GhArchiveAdapter.EXAMPLE_QUERY
    assert "swh" in SoftwareHeritageAdapter.EXAMPLE_QUERY.lower()
    with pytest.raises(FileNotFoundError):
        GhArchiveAdapter(Path("/no/such/gharchive")).fetch_velocity("org/repo")
