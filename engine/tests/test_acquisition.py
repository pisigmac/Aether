from pathlib import Path

import pytest

from aether.acquisition.adapters import GhArchiveAdapter, SoftwareHeritageAdapter
from aether.acquisition.licenses import detect_license, license_allowed
from aether.acquisition.sampler import sample_commits


def test_license_allowlist(tmp_path: Path):
    (tmp_path / "LICENSE").write_text("MIT License\nPermission is hereby granted, free of charge", encoding="utf-8")
    assert detect_license(tmp_path) == "MIT"
    assert license_allowed("MIT")
    assert not license_allowed("GPL-3.0")


def test_sample_working_tree(tmp_path: Path):
    samples = sample_commits(tmp_path)
    assert len(samples) == 1
    assert samples[0].sha == "WORKING_TREE"


def test_adapters_are_stubs():
    with pytest.raises(NotImplementedError):
        GhArchiveAdapter().fetch_velocity("org/repo")
    with pytest.raises(NotImplementedError):
        SoftwareHeritageAdapter().fetch_history("https://github.com/org/repo")
    assert "PushEvent" in GhArchiveAdapter.EXAMPLE_QUERY
    assert "swh" in SoftwareHeritageAdapter.EXAMPLE_QUERY.lower()
