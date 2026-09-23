from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Protocol

from aether.ir.models import EvolutionRecord, MetricVector

VECTOR_KEYS = (
    "mass",
    "coupling",
    "churn",
    "cycles",
    "god_module_count",
    "contract_leak_count",
)
DELTA_KEYS = ("nodes_added", "nodes_removed", "edges_added", "edges_removed")
FEATURE_VELOCITY = 1.0
PATTERN_LABELS = (
    "god_module",
    "cyclic_dep",
    "schema_leak",
    "chatty_rpc",
    "unbounded_list",
    "missing_index",
    "dual_write",
)


class Predictor(Protocol):
    name: str
    model_id: str
    training_records: int

    def predict(self, current: MetricVector, delta: dict[str, int], velocity: float) -> MetricVector: ...


class HeuristicPredictor:
    """Identity: next vector ≈ current. Phase 1 default."""

    name = "heuristic"
    model_id = "heuristic"
    training_records = 0

    def predict(self, current: MetricVector, delta: dict[str, int], velocity: float) -> MetricVector:
        _ = delta, velocity
        return current.model_copy()

    def predict_labels(self, current: MetricVector, delta: dict[str, int], velocity: float) -> list[str] | None:
        _ = current, delta, velocity
        return None


class LinearPredictor:
    """Ridge regressor: horizon_target from current vector + delta + velocity."""

    name = "learned"
    model_id = "time-machine-v1"

    def __init__(
        self,
        weights: list[list[float]],
        bias: list[float],
        training_records: int = 0,
        pattern_weights: list[list[float]] | None = None,
        pattern_bias: list[float] | None = None,
        target: str = "absolute",
        feat_mean: list[float] | None = None,
        feat_std: list[float] | None = None,
        residual_clip: list[float] | None = None,
        dim_gate: list[int] | None = None,
    ) -> None:
        self.weights = weights
        self.bias = bias
        self.training_records = training_records
        self.pattern_weights = pattern_weights or []
        self.pattern_bias = pattern_bias or []
        self.target = target if target in {"absolute", "residual"} else "absolute"
        self.feat_mean = feat_mean or []
        self.feat_std = feat_std or []
        self.residual_clip = residual_clip or []
        self.dim_gate = dim_gate or []

    def predict(self, current: MetricVector, delta: dict[str, int], velocity: float) -> MetricVector:
        _ = velocity
        x = _standardize(
            _features(current, delta, FEATURE_VELOCITY, log_mass=self.target == "residual"),
            self.feat_mean,
            self.feat_std,
        )
        values = [_dot(row, x) + b for row, b in zip(self.weights, self.bias)]
        if self.target == "residual":
            current_row = _vector_row(current)
            gated = self.dim_gate or [1] * len(values)
            clipped = self.residual_clip
            merged: list[float] = []
            for i, (cur, resid) in enumerate(zip(current_row, values)):
                if i < len(gated) and not gated[i]:
                    merged.append(cur)
                    continue
                if i < len(clipped) and clipped[i] > 0:
                    cap = clipped[i]
                    resid = max(-cap, min(cap, resid))
                merged.append(cur + resid)
            values = merged
        return MetricVector(
            mass=max(0.0, values[0]),
            coupling=max(0.0, values[1]),
            churn=max(0.0, values[2]),
            cycles=max(0, int(round(values[3]))),
            god_module_count=max(0, int(round(values[4]))),
            contract_leak_count=max(0, int(round(values[5]))),
        )

    def predict_labels(self, current: MetricVector, delta: dict[str, int], velocity: float) -> list[str] | None:
        if not self.pattern_weights or not self.pattern_bias:
            return None
        _ = velocity
        x = _standardize(
            _features(current, delta, FEATURE_VELOCITY, log_mass=True),
            self.feat_mean,
            self.feat_std,
        )
        labels: list[str] = []
        for name, row, b in zip(PATTERN_LABELS, self.pattern_weights, self.pattern_bias):
            if _dot(row, x) + b >= 0.5:
                labels.append(name)
        return labels

    def dump(self) -> dict:
        data = {
            "model_id": self.model_id,
            "training_records": self.training_records,
            "weights": self.weights,
            "bias": self.bias,
            "target": self.target,
            "feat_mean": self.feat_mean,
            "feat_std": self.feat_std,
            "residual_clip": self.residual_clip,
            "dim_gate": self.dim_gate,
        }
        if self.pattern_weights and self.pattern_bias:
            data["pattern_weights"] = self.pattern_weights
            data["pattern_bias"] = self.pattern_bias
            data["pattern_labels"] = list(PATTERN_LABELS)
        return data

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.dump(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> LinearPredictor:
        data = json.loads(path.read_text(encoding="utf-8"))
        model = cls(
            data["weights"],
            data["bias"],
            int(data.get("training_records") or 0),
            pattern_weights=data.get("pattern_weights") or [],
            pattern_bias=data.get("pattern_bias") or [],
            target=str(data.get("target") or "absolute"),
            feat_mean=[float(x) for x in (data.get("feat_mean") or [])],
            feat_std=[float(x) for x in (data.get("feat_std") or [])],
            residual_clip=[float(x) for x in (data.get("residual_clip") or [])],
            dim_gate=[int(x) for x in (data.get("dim_gate") or [])],
        )
        model.model_id = str(data.get("model_id") or model.model_id)
        return model


def train_linear(records: list[EvolutionRecord], ridge: float = 1e-2) -> LinearPredictor:
    labeled = [r for r in records if r.horizon_target is not None]
    if len(labeled) < 2:
        raise ValueError("Need at least 2 Evolution Records with horizon_target to train.")
    xs_raw = [_features(r.metric_vector, r.delta_from_prev, FEATURE_VELOCITY, log_mass=True) for r in labeled]
    feat_mean, feat_std = _mean_std(xs_raw)
    xs = [_standardize(row, feat_mean, feat_std) for row in xs_raw]
    residuals = [
        [t - c for t, c in zip(_vector_row(r.horizon_target), _vector_row(r.metric_vector))]
        for r in labeled
        if r.horizon_target
    ]
    weights: list[list[float]] = []
    bias: list[float] = []
    residual_clip: list[float] = []
    dim_gate: list[int] = []
    for col in range(len(VECTOR_KEYS)):
        col_y = [row[col] for row in residuals]
        w, b = _ridge_fit(xs, col_y, ridge)
        weights.append(w)
        bias.append(b)
        identity_err = sum(abs(y) for y in col_y)
        loocv_err = _loocv_mae(xs, col_y, ridge)
        dim_gate.append(1 if loocv_err + 1e-9 < identity_err else 0)
        residual_clip.append(max(_percentile([abs(y) for y in col_y], 0.5), 1e-3))
    pattern_weights, pattern_bias = _train_pattern_head(records, ridge, feat_mean, feat_std)
    return LinearPredictor(
        weights,
        bias,
        training_records=len(labeled),
        pattern_weights=pattern_weights,
        pattern_bias=pattern_bias,
        target="residual",
        feat_mean=feat_mean,
        feat_std=feat_std,
        residual_clip=residual_clip,
        dim_gate=dim_gate,
    )


def _consecutive_pairs(records: list[EvolutionRecord]) -> list[tuple[EvolutionRecord, EvolutionRecord]]:
    by_repo: dict[str, list[EvolutionRecord]] = {}
    for rec in records:
        by_repo.setdefault(rec.repo_id, []).append(rec)
    pairs: list[tuple[EvolutionRecord, EvolutionRecord]] = []
    for group in by_repo.values():
        group.sort(key=lambda r: (r.authored_at, r.commit_sha))
        for prev, nxt in zip(group, group[1:]):
            pairs.append((prev, nxt))
    return pairs


def _train_pattern_head(
    records: list[EvolutionRecord],
    ridge: float,
    feat_mean: list[float],
    feat_std: list[float],
) -> tuple[list[list[float]], list[float]]:
    pairs = _consecutive_pairs(records)
    if len(pairs) < 2:
        return [], []
    if not any(nxt.pattern_labels for _prev, nxt in pairs):
        return [], []
    xs = [
        _standardize(
            _features(prev.metric_vector, prev.delta_from_prev, FEATURE_VELOCITY, log_mass=True),
            feat_mean,
            feat_std,
        )
        for prev, _nxt in pairs
    ]
    weights: list[list[float]] = []
    bias: list[float] = []
    for label in PATTERN_LABELS:
        ys = [1.0 if label in nxt.pattern_labels else 0.0 for _prev, nxt in pairs]
        w, b = _ridge_fit(xs, ys, ridge)
        weights.append(w)
        bias.append(b)
    return weights, bias


def mae(records: list[EvolutionRecord], predictor: Predictor) -> float:
    labeled = [r for r in records if r.horizon_target is not None]
    if not labeled:
        return 0.0
    total = 0.0
    for rec in labeled:
        pred = predictor.predict(rec.metric_vector, rec.delta_from_prev, 1.0)
        actual = rec.horizon_target
        assert actual is not None
        total += _l1(_vector_row(pred), _vector_row(actual))
    return total / len(labeled)


def resolve_predictor(model_path: Path | None) -> Predictor:
    if model_path and model_path.is_file():
        return LinearPredictor.load(model_path)
    return HeuristicPredictor()


def predictor_for_mode(mode: str, model_path: Path | None = None) -> Predictor:
    """Select heuristic, learned, or auto (learned if a model file exists)."""
    normalized = (mode or "auto").strip().lower()
    if normalized not in {"auto", "heuristic", "learned"}:
        raise ValueError("mode must be auto, heuristic, or learned")
    if normalized == "heuristic":
        return HeuristicPredictor()
    if normalized == "learned":
        predictor = resolve_predictor(model_path)
        if predictor.name != "learned":
            raise FileNotFoundError("No learned model loaded. Train one and set AETHER_MODEL_PATH.")
        return predictor
    return resolve_predictor(model_path)


def _features(
    current: MetricVector,
    delta: dict[str, int],
    velocity: float,
    log_mass: bool = False,
) -> list[float]:
    mass = float(current.mass)
    mass_feat = math.log1p(max(mass, 0.0)) if log_mass else mass
    return [
        mass_feat,
        float(current.coupling),
        float(current.churn),
        float(current.cycles),
        float(current.god_module_count),
        float(current.contract_leak_count),
        *[float(delta.get(key, 0)) for key in DELTA_KEYS],
        float(velocity),
    ]


def _mean_std(xs: list[list[float]]) -> tuple[list[float], list[float]]:
    n = len(xs)
    d = len(xs[0])
    mean = [sum(row[i] for row in xs) / n for i in range(d)]
    std: list[float] = []
    for i in range(d):
        var = sum((row[i] - mean[i]) ** 2 for row in xs) / n
        std.append(math.sqrt(var) if var > 1e-12 else 1.0)
    return mean, std


def _standardize(row: list[float], mean: list[float], std: list[float]) -> list[float]:
    if not mean or not std or len(mean) != len(row) or len(std) != len(row):
        return row
    return [(value - m) / (s or 1.0) for value, m, s in zip(row, mean, std)]


def _loocv_mae(xs: list[list[float]], ys: list[float], ridge: float) -> float:
    if len(xs) < 3:
        return sum(abs(y) for y in ys)
    total = 0.0
    for i in range(len(xs)):
        w, b = _ridge_fit(xs[:i] + xs[i + 1 :], ys[:i] + ys[i + 1 :], ridge)
        total += abs(_dot(w, xs[i]) + b - ys[i])
    return total


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return ordered[idx]


def _vector_row(vec: MetricVector) -> list[float]:
    return [float(getattr(vec, key)) for key in VECTOR_KEYS]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _l1(a: list[float], b: list[float]) -> float:
    return sum(abs(x - y) for x, y in zip(a, b))


def _ridge_fit(xs: list[list[float]], ys: list[float], ridge: float) -> tuple[list[float], float]:
    """Fit y ≈ w·x + b with a small ridge. Closed form on the augmented matrix."""
    n = len(xs)
    d = len(xs[0]) + 1
    xtx = [[0.0] * d for _ in range(d)]
    xty = [0.0] * d
    for x, y in zip(xs, ys):
        row = [*x, 1.0]
        for i in range(d):
            xty[i] += row[i] * y
            for j in range(d):
                xtx[i][j] += row[i] * row[j]
    for i in range(d - 1):
        xtx[i][i] += ridge
    solved = _solve(xtx, xty)
    return solved[:-1], solved[-1]


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(a)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for i in range(n):
        pivot = max(range(i, n), key=lambda r: abs(m[r][i]))
        m[i], m[pivot] = m[pivot], m[i]
        diag = m[i][i] or 1e-12
        for j in range(i, n + 1):
            m[i][j] /= diag
        for r in range(n):
            if r == i:
                continue
            factor = m[r][i]
            for j in range(i, n + 1):
                m[r][j] -= factor * m[i][j]
    return [m[i][n] for i in range(n)]


def scale_from_prediction(current: MetricVector, predicted: MetricVector) -> float:
    denom = max(current.mass, 0.1)
    raw = predicted.mass / denom
    if math.isnan(raw) or raw <= 0:
        return 1.0
    return min(max(raw, 0.25), 4.0)
