from __future__ import annotations

from aether.ir.models import EvolutionRecord
from aether.physics.predictor import HeuristicPredictor, LinearPredictor, mae, train_linear


def frozen_split(
    records: list[EvolutionRecord],
    test_fraction: float = 0.3,
) -> tuple[list[EvolutionRecord], list[EvolutionRecord]]:
    """Per-repo chronological hold-out. Later history is test. No shuffle."""
    labeled = [r for r in records if r.horizon_target is not None]
    if len(labeled) < 3:
        raise ValueError("Need at least 3 Evolution Records with horizon_target for a frozen split.")
    frac = min(max(test_fraction, 0.1), 0.5)
    by_repo: dict[str, list[EvolutionRecord]] = {}
    for rec in labeled:
        by_repo.setdefault(rec.repo_id, []).append(rec)
    train: list[EvolutionRecord] = []
    test: list[EvolutionRecord] = []
    for group in by_repo.values():
        group.sort(key=lambda r: (r.authored_at, r.commit_sha))
        if len(group) == 1:
            train.extend(group)
            continue
        if len(group) < 3:
            train.extend(group[:-1])
            test.extend(group[-1:])
            continue
        cut = max(2, int(len(group) * (1.0 - frac)))
        if cut >= len(group):
            cut = len(group) - 1
        train.extend(group[:cut])
        test.extend(group[cut:])
    if len(train) < 2 or not test:
        raise ValueError("Frozen split produced too few rows.")
    train.sort(key=lambda r: (r.authored_at, r.commit_sha))
    test.sort(key=lambda r: (r.authored_at, r.commit_sha))
    return train, test


def evaluate_time_machine(
    records: list[EvolutionRecord],
    test_fraction: float = 0.3,
) -> dict:
    train, test = frozen_split(records, test_fraction)
    model = train_linear(train)
    learned_mae = mae(test, model)
    heuristic_mae = mae(test, HeuristicPredictor())
    return {
        "split": "chronological_per_repo",
        "test_fraction": test_fraction,
        "train_n": len(train),
        "test_n": len(test),
        "train_until": train[-1].authored_at,
        "test_from": test[0].authored_at,
        "learned_mae": round(learned_mae, 6),
        "heuristic_mae": round(heuristic_mae, 6),
        "beats_heuristic": learned_mae < heuristic_mae,
        "model_id": model.model_id,
        "training_records": model.training_records,
        "pattern_head": bool(model.pattern_weights),
    }


def train_and_report(records: list[EvolutionRecord]) -> tuple[LinearPredictor, dict]:
    model = train_linear(records)
    report = evaluate_time_machine(records)
    return model, report
