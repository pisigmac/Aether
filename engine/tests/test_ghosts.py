import subprocess
import threading
import time

from aether.ir.models import GhostResult
from aether.physics.ghosts import (
    PHASE1_INTENTS,
    AgentGhostRunner,
    CATALOG,
    HeuristicGhostRunner,
    disclose_parallel,
    parallel_width,
    run_ghost_lab,
)
from aether.physics.sandbox import open_sandbox, write_ghost_artifact
from tests.test_physics import _snap


def test_default_lab_stays_heuristic():
    snap = _snap("a", "2026-01-01T00:00:00+00:00")
    ghosts = run_ghost_lab(snap)
    assert {g.intent for g in ghosts} == {item.intent for item in CATALOG}
    assert all("attach via" in g.note.lower() for g in ghosts)
    assert HeuristicGhostRunner().name == "heuristic"


def test_agent_runner_same_catalog_does_not_mutate_snapshot():
    snap = _snap("a", "2026-01-01T00:00:00+00:00")
    before = (len(snap.nodes), len(snap.edges), [n.id for n in snap.nodes])
    ghosts = run_ghost_lab(snap, AgentGhostRunner())
    assert (len(snap.nodes), len(snap.edges), [n.id for n in snap.nodes]) == before
    assert {g.intent for g in ghosts} == {item.intent for item in CATALOG}
    assert all(g.note.startswith("Agent run:") for g in ghosts)
    assert all(g.verdict in {"pass", "warn", "fail"} for g in ghosts)
    assert all(g.files_touched for g in ghosts)
    assert AgentGhostRunner().name == "agent"
    assert all(ghost.ir_only for ghost in ghosts)
    assert all(ghost.ir_mutation.startswith("add module ghost:") for ghost in ghosts)


def test_phase1_intents_stay_and_v2_is_added():
    assert len(PHASE1_INTENTS) == 8
    assert {"add_openapi_client", "extract_service", "add_queue"} <= {item.intent for item in CATALOG}
    ghosts = run_ghost_lab(_snap("a", "2026-01-01T00:00:00+00:00"))
    assert [ghost.intent for ghost in ghosts][:8] == list(PHASE1_INTENTS)
    assert all("attach via" in ghost.note.lower() for ghost in ghosts)
    assert all(ghost.ir_only is False for ghost in ghosts)


def test_sandbox_worktree_leaves_the_dirty_tree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "keep.txt").write_text("dirty")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "add", "keep.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=a@b.c", "-c", "user.name=Aether", "commit", "-m", "keep"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "keep.txt").write_text("dirtier")
    sandbox = open_sandbox(str(repo), tmp_path / "sandboxes")
    artifact = write_ghost_artifact(sandbox, "add_queue")
    assert (repo / "keep.txt").read_text() == "dirtier"
    assert not (repo / "ghost").exists()
    assert artifact.is_relative_to(sandbox.resolve())
    assert not sandbox.resolve().is_relative_to(repo.resolve())
    assert "not applied" in artifact.read_text()


def test_parallel_cap_discloses_width():
    assert parallel_width(4) == 4
    assert "4 ghosts run in parallel (hard max 16)" in disclose_parallel(4)
    try:
        parallel_width(17)
    except ValueError:
        pass
    else:
        raise AssertionError("expected the hard max to reject 17")

    class _Slow:
        name = "slow"

        def __init__(self):
            self.current = 0
            self.max_seen = 0
            self.lock = threading.Lock()

        def run(self, snapshot, intent):
            with self.lock:
                self.current += 1
                self.max_seen = max(self.max_seen, self.current)
            time.sleep(0.02)
            with self.lock:
                self.current -= 1
            return GhostResult(
                intent=intent.intent,
                title=intent.title,
                verdict="pass",
                extensibility=1,
                note="Agent run: parallel",
            )

    runner = _Slow()
    ghosts = run_ghost_lab(_snap("a", "2026-01-01T00:00:00+00:00"), runner, parallel=4)
    assert [ghost.intent for ghost in ghosts] == [item.intent for item in CATALOG]
    assert 1 < runner.max_seen <= 4