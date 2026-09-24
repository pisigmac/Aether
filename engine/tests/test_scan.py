import sys
from pathlib import Path

from aether.acquisition.sampler import batch_show_files, sample_commits, show_file
from aether.parsers.scan import parse_history, parse_snapshot

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "polyglot-debt"


def _seed() -> None:
    sys.path.insert(0, str(FIXTURE))
    import seed_git

    seed_git.main()


def test_batch_show_matches_show_file():
    _seed()
    samples = sample_commits(FIXTURE, max_samples=3)
    sha = samples[-1].sha
    one = show_file(FIXTURE, "backend/app.py", sha)
    many = batch_show_files(FIXTURE, sha, ["backend/app.py", "missing.py"])
    assert many["backend/app.py"] == one
    assert "missing.py" not in many


def test_history_matches_full_snapshot_parse():
    _seed()
    samples = sample_commits(FIXTURE)
    full = [parse_snapshot(FIXTURE, sample) for sample in samples]
    incremental = parse_history(FIXTURE, samples)
    assert len(incremental) == len(full)
    for left, right in zip(full, incremental):
        assert right.snapshot_hash == left.snapshot_hash
        assert {node.id for node in right.nodes} == {node.id for node in left.nodes}
        assert {(edge.src, edge.dst, edge.kind) for edge in right.edges} == {
            (edge.src, edge.dst, edge.kind) for edge in left.edges
        }
