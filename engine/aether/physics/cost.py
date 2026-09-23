from __future__ import annotations

import json
from pathlib import Path

from aether.ir.models import CostBand, Snapshot
from aether.physics.metrics import detect_patterns

DEFAULT_DRIVERS: dict[str, dict[str, float]] = {
    "unbounded_list": {"compute": 4.0, "storage": 0.4, "egress": 8.0},
    "chatty_rpc": {"compute": 6.0, "storage": 0.1, "egress": 2.5},
    "dual_write": {"compute": 2.0, "storage": 3.5, "egress": 0.5},
    "missing_index": {"compute": 7.0, "storage": 0.2, "egress": 0.2},
    "schema_leak": {"compute": 1.5, "storage": 1.0, "egress": 3.0},
    "god_module": {"compute": 1.2, "storage": 0.1, "egress": 0.1},
    "cyclic_dep": {"compute": 1.8, "storage": 0.1, "egress": 0.2},
}


def load_drivers(path: Path | None = None) -> dict[str, dict[str, float]]:
    if path and path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    bundled = Path(__file__).resolve().parents[3] / "datasets" / "cost_drivers.json"
    if bundled.is_file():
        return load_drivers(bundled)
    return DEFAULT_DRIVERS


def build_costs(
    snapshot: Snapshot,
    horizon_months: int,
    velocity: float,
    traffic_growth: float = 0.08,
    drivers: dict[str, dict[str, float]] | None = None,
    labels: list[str] | None = None,
) -> list[CostBand]:
    table = drivers or load_drivers()
    labels = detect_patterns(snapshot) if labels is None else list(labels)
    base = {"compute": 12.0, "storage": 4.0, "egress": 3.0}
    for label in labels:
        inc = table.get(label)
        if not inc:
            continue
        for key in base:
            base[key] += inc.get(key, 0.0)

    bands: list[CostBand] = []
    growth = 1.0 + max(traffic_growth, 0.0)
    vel_factor = 1.0 + min(velocity, 20.0) / 40.0
    for month in range(0, horizon_months + 1, 3 if horizon_months >= 12 else 1):
        t = max(month, 0)
        scale = (growth ** (t / 3.0)) * vel_factor
        bands.append(
            CostBand(
                month=t,
                compute=round(base["compute"] * scale, 2),
                storage=round(base["storage"] * (1.0 + t * 0.04) * scale, 2),
                egress=round(base["egress"] * scale, 2),
                drivers=labels,
            )
        )
    return bands
