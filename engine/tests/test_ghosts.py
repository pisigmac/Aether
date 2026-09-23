from aether.physics.ghosts import AgentGhostRunner, CATALOG, HeuristicGhostRunner, run_ghost_lab
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