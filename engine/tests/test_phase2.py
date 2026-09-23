import gzip
import json
from pathlib import Path

from aether.acquisition.adapters import GhArchiveAdapter, SoftwareHeritageAdapter
from aether.cli import main
from aether.corpus import load_manifest, seed_corpus
from aether.eval import evaluate_time_machine, frozen_split
from aether.export import export_evolution, load_evolution_jsonl
from aether.ir.models import EvolutionRecord, MetricVector, Universe
from aether.physics.cost import build_costs
from aether.physics.forecast import build_forecast
from aether.physics.metrics import metric_vector, node_metrics
from aether.physics.predictor import (
    HeuristicPredictor,
    LinearPredictor,
    mae,
    predictor_for_mode,
    train_linear,
)
from aether.storage.db import AetherDB
from tests.test_physics import _snap


def _dump_events(path: Path) -> None:
    events = [
        {
            "type": "PushEvent",
            "repo": {"name": "lukeed/clsx"},
            "actor": {"login": "lukeed"},
            "created_at": "2026-01-01T00:00:00Z",
            "payload": {"commits": [{"sha": "a"}, {"sha": "b"}]},
        },
        {
            "type": "PushEvent",
            "repo": {"name": "lukeed/clsx"},
            "actor": {"login": "alice"},
            "created_at": "2026-01-15T00:00:00Z",
            "payload": {"commits": [{"sha": "c"}]},
        },
        {
            "type": "WatchEvent",
            "repo": {"name": "lukeed/clsx"},
            "created_at": "2026-01-15T00:00:00Z",
        },
    ]
    path.write_bytes(gzip.compress(("\n".join(json.dumps(e) for e in events) + "\n").encode()))


def test_gharchive_velocity(tmp_path: Path):
    dump = tmp_path / "2026-01-01-0.json.gz"
    _dump_events(dump)
    out = GhArchiveAdapter(tmp_path).fetch_velocity("lukeed/clsx")
    assert out["push_events"] == 2
    assert out["actors"] == 2
    assert out["commits_per_week"] > 0


def test_swh_history_uses_web_api():
    fixture = {
        "https://archive.softwareheritage.org/api/1/origin/https%3A%2F%2Fgithub.com%2Flukeed%2Fclsx/get/": {
            "url": "https://github.com/lukeed/clsx"
        },
        "https://archive.softwareheritage.org/api/1/origin/https%3A%2F%2Fgithub.com%2Flukeed%2Fclsx/visits/?per_page=5": [
            {"date": "2026-01-02T00:00:00+00:00", "snapshot": "aaa"}
        ],
        "https://archive.softwareheritage.org/api/1/snapshot/aaa/": {
            "branches": {"refs/heads/main": {"target_type": "revision", "target": "bbb"}}
        },
        "https://archive.softwareheritage.org/api/1/revision/bbb/": {
            "directory": "ccc",
            "date": "2026-01-01T00:00:00+00:00",
            "message": "release",
        },
    }

    def getter(url: str):
        return fixture[url]

    rows = SoftwareHeritageAdapter(http_get=getter).fetch_history("https://github.com/lukeed/clsx")
    assert rows[0]["revision"] == "swh:1:rev:bbb"
    assert rows[0]["directory"] == "swh:1:dir:ccc"


def test_linear_predictor_beats_heuristic():
    records = []
    for i in range(8):
        current = MetricVector(mass=10 + i, coupling=1, churn=0.2, cycles=1, god_module_count=1, contract_leak_count=0)
        target = MetricVector(mass=20 + i * 2, coupling=2, churn=0.4, cycles=2, god_module_count=2, contract_leak_count=1)
        records.append(
            EvolutionRecord(
                repo_id="r",
                commit_sha=f"c{i}",
                authored_at=f"2026-01-0{i + 1}T00:00:00+00:00" if i < 9 else "2026-01-10T00:00:00+00:00",
                snapshot_hash=f"h{i}",
                metric_vector=current,
                horizon_target=target,
                delta_from_prev={"nodes_added": 2, "nodes_removed": 0, "edges_added": 1, "edges_removed": 0},
            )
        )
    model = train_linear(records)
    assert mae(records, model) < mae(records, HeuristicPredictor())


def test_export_and_cli_roundtrip(tmp_path: Path):
    db = AetherDB(tmp_path / "aether.db")
    rec = EvolutionRecord(
        repo_id="r",
        commit_sha="abc",
        authored_at="2026-01-01T00:00:00+00:00",
        snapshot_hash="h",
        metric_vector=MetricVector(mass=4),
        horizon_target=MetricVector(mass=5),
    )
    db.upsert_evolution(rec)
    out = tmp_path / "evo.jsonl"
    assert export_evolution(db, out) == 1
    loaded = load_evolution_jsonl(out)
    assert loaded[0].horizon_target is not None
    assert loaded[0].horizon_target.mass == 5

    model_out = tmp_path / "model.json"
    train_in = tmp_path / "train.jsonl"
    rec2 = EvolutionRecord(
        repo_id="r",
        commit_sha="def",
        authored_at="2026-01-02T00:00:00+00:00",
        snapshot_hash="i",
        metric_vector=MetricVector(mass=6),
        horizon_target=MetricVector(mass=8),
        delta_from_prev={"nodes_added": 1, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0},
    )
    with train_in.open("w", encoding="utf-8") as fh:
        fh.write(rec.model_dump_json() + "\n")
        fh.write(rec2.model_dump_json() + "\n")
    assert main(["train-time-machine", "--in", str(train_in), "--out", str(model_out)]) == 0
    assert model_out.is_file()

    snaps = [_snap("a", "2025-01-01T00:00:00+00:00"), _snap("b", "2026-01-01T00:00:00+00:00")]
    universe = Universe(id="u", repo_path="/tmp/x", snapshots=snaps, velocity_commits_per_week=2)
    from aether.physics.predictor import LinearPredictor

    learned = LinearPredictor.load(model_out)
    bundle = build_forecast(universe, predictor=learned)
    assert bundle.heuristic is False
    assert bundle.model_id
    assert "Learned model" in bundle.warnings[0]


def test_corpus_manifest():
    manifest = load_manifest()
    assert {r["spdx"] for r in manifest["repos"]} <= {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}
    assert len(manifest["repos"]) >= 3
    assert all("swhids" in r and "url" in r for r in manifest["repos"])


def _growing_records(n: int = 12, labels: list[str] | None = None) -> list[EvolutionRecord]:
    rows: list[EvolutionRecord] = []
    for i in range(n):
        day = i + 1
        current = MetricVector(mass=10 + i, coupling=1, churn=0.2, cycles=1, god_module_count=1, contract_leak_count=0)
        target = MetricVector(mass=12 + i, coupling=1.2, churn=0.25, cycles=1, god_module_count=1, contract_leak_count=0)
        rows.append(
            EvolutionRecord(
                repo_id="r",
                commit_sha=f"c{i}",
                authored_at=f"2026-01-{day:02d}T00:00:00+00:00",
                snapshot_hash=f"h{i}",
                metric_vector=current,
                pattern_labels=list(labels or []),
                horizon_target=target,
                delta_from_prev={"nodes_added": 1, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0},
            )
        )
    return rows


def test_frozen_split_is_chronological():
    records = _growing_records()
    train, test = frozen_split(records, 0.3)
    assert train
    assert test
    assert train[-1].authored_at < test[0].authored_at
    assert all(r.horizon_target is not None for r in train + test)


def test_eval_time_machine_beats_heuristic_on_holdout():
    report = evaluate_time_machine(_growing_records())
    assert report["split"] == "chronological_per_repo"
    assert report["train_n"] >= 2
    assert report["test_n"] >= 1
    assert report["learned_mae"] < report["heuristic_mae"]
    assert report["beats_heuristic"] is True


def test_eval_cli(tmp_path: Path):
    source = tmp_path / "evo.jsonl"
    source.write_text("\n".join(r.model_dump_json() for r in _growing_records()) + "\n", encoding="utf-8")
    out = tmp_path / "eval.json"
    assert main(["eval-time-machine", "--in", str(source), "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["beats_heuristic"] is True


def test_heuristic_costs_match_direct_build():
    snaps = [_snap("a", "2025-01-01T00:00:00+00:00"), _snap("b", "2026-01-01T00:00:00+00:00")]
    universe = Universe(id="u", repo_path="/tmp/x", snapshots=snaps, velocity_commits_per_week=2)
    bundle = build_forecast(universe, horizon_months=24)
    assert bundle.heuristic is True
    direct = build_costs(snaps[-1], 24, 2.0)
    assert [c.model_dump() for c in bundle.costs] == [c.model_dump() for c in direct]


def test_learned_without_pattern_head_keeps_detect_patterns():
    records = _growing_records()
    model = train_linear(records)
    assert model.pattern_weights == []
    snaps = [_snap("a", "2025-01-01T00:00:00+00:00")]
    universe = Universe(id="u", repo_path="/tmp/x", snapshots=snaps, velocity_commits_per_week=2)
    bundle = build_forecast(universe, predictor=model)
    assert bundle.heuristic is False
    assert bundle.costs[0].drivers == build_costs(snaps[-1], 24, 2.0)[0].drivers


def test_pattern_head_drives_cost_horizon_only(tmp_path: Path):
    labeled = []
    for i in range(8):
        god = i >= 4
        labeled.append(
            EvolutionRecord(
                repo_id="r",
                commit_sha=f"c{i}",
                authored_at=f"2026-01-{i + 1:02d}T00:00:00+00:00",
                snapshot_hash=f"h{i}",
                metric_vector=MetricVector(
                    mass=30 if god else 8,
                    coupling=2 if god else 0.4,
                    churn=0.4,
                    cycles=0,
                    god_module_count=1 if god else 0,
                    contract_leak_count=0,
                ),
                pattern_labels=["god_module"] if god else [],
                horizon_target=MetricVector(mass=32 if god else 9, coupling=2, churn=0.4, cycles=0, god_module_count=1 if god else 0),
                delta_from_prev={"nodes_added": 2 if god else 0, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0},
            )
        )
    model = train_linear(labeled)
    assert model.pattern_weights
    predicted = model.predict_labels(labeled[-1].metric_vector, labeled[-1].delta_from_prev, 1.0)
    assert predicted is not None
    assert "god_module" in predicted
    model.save(tmp_path / "model.json")
    loaded = LinearPredictor.load(tmp_path / "model.json")
    assert loaded.pattern_weights

    snaps = [_snap("a", "2025-01-01T00:00:00+00:00")]
    universe = Universe(id="u", repo_path="/tmp/x", snapshots=snaps, velocity_commits_per_week=2)
    heuristic = build_forecast(universe)
    learned = build_forecast(universe, predictor=loaded)
    vec = metric_vector(snaps[-1], node_metrics(snaps[-1]))
    predicted = loaded.predict_labels(
        vec, {"nodes_added": 0, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0}, 2.0
    )
    assert heuristic.heuristic is True
    assert "unbounded_list" in heuristic.costs[0].drivers
    assert learned.heuristic is False
    assert learned.costs[0].drivers == list(predicted or [])


def _mixed_scale_records() -> list[EvolutionRecord]:
    rows: list[EvolutionRecord] = []
    for repo, base, step, n in (("small", 19.0, 0.04, 8), ("large", 410.0, 0.18, 8)):
        for i in range(n):
            mass = base + step * i
            rows.append(
                EvolutionRecord(
                    repo_id=repo,
                    commit_sha=f"{repo}-{i}",
                    authored_at=f"2026-01-{i + 1:02d}T00:00:00+00:00",
                    snapshot_hash=f"{repo}{i}",
                    metric_vector=MetricVector(mass=mass, coupling=1 if repo == "small" else 5, churn=0.15),
                    horizon_target=MetricVector(mass=mass + step, coupling=1 if repo == "small" else 5, churn=0.15),
                    delta_from_prev={"nodes_added": 1, "nodes_removed": 0, "edges_added": 0, "edges_removed": 0},
                )
            )
    return rows


def test_residual_model_beats_heuristic_on_mixed_scale():
    records = _mixed_scale_records()
    report = evaluate_time_machine(records)
    assert report["beats_heuristic"] is True
    assert report["learned_mae"] < report["heuristic_mae"]


def test_seed_holdout_does_not_lose_to_heuristic_when_export_present():
    path = Path(__file__).resolve().parents[1] / "data" / "seed-evolution.jsonl"
    if not path.is_file():
        return
    report = evaluate_time_machine(load_evolution_jsonl(path))
    assert report["test_n"] >= 3
    # Seed snapshots jump an order of magnitude; LOOCV gates noisy dims so we do not lose.
    assert report["learned_mae"] <= report["heuristic_mae"] + 1e-6


def test_predictor_for_mode(tmp_path: Path):
    assert predictor_for_mode("heuristic").name == "heuristic"
    try:
        predictor_for_mode("learned", tmp_path / "missing.json")
        raise AssertionError("expected missing model")
    except FileNotFoundError:
        pass
    records = _growing_records(6)
    model = train_linear(records)
    out = tmp_path / "model.json"
    model.save(out)
    learned = predictor_for_mode("learned", out)
    assert learned.name == "learned"
    assert predictor_for_mode("auto", None).name == "heuristic"


def test_old_model_json_loads_without_pattern_head(tmp_path: Path):
    path = tmp_path / "old.json"
    path.write_text(
        json.dumps(
            {
                "model_id": "time-machine-v1",
                "training_records": 2,
                "weights": [[0.0] * 11 for _ in range(6)],
                "bias": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            }
        ),
        encoding="utf-8",
    )
    model = LinearPredictor.load(path)
    assert model.target == "absolute"
    assert model.predict_labels(MetricVector(mass=4), {}, 1.0) is None
    assert model.predict(MetricVector(mass=4), {}, 1.0).mass == 1.0


def test_seed_corpus_local(tmp_path: Path):
    import sys

    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "polyglot-debt"
    sys.path.insert(0, str(fixture))
    import seed_git

    seed_git.main()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "ir_version": 1,
                "repos": [
                    {
                        "name": "polyglot-debt",
                        "url": "https://example.invalid/polyglot-debt",
                        "spdx": "MIT",
                        "swhids": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    db = AetherDB(tmp_path / "aether.db")
    rows = seed_corpus(
        db,
        manifest,
        lookback_months=36,
        max_samples=8,
        local_overrides={"polyglot-debt": str(fixture)},
    )
    assert rows[0]["ok"] is True
    assert rows[0]["snapshots"] >= 2
    assert rows[0]["horizon_target_records"] >= 1
    assert rows[0]["license"] == "MIT"
    assert main(
        [
            "seed-corpus",
            "--db",
            str(tmp_path / "cli.db"),
            "--manifest",
            str(manifest),
            "--local",
            f"polyglot-debt={fixture}",
            "--max-samples",
            "4",
        ]
    ) == 0
