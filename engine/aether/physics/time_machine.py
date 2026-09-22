from __future__ import annotations

from aether.ir.models import Collision, NodeMetrics, Snapshot, TimelineFrame
from aether.physics.metrics import detect_patterns, node_metrics, path_churn


def _smooth(series: list[float], alpha: float = 0.45) -> float:
    if not series:
        return 0.0
    value = series[0]
    for item in series[1:]:
        value = alpha * item + (1 - alpha) * value
    return value


def _slope(series: list[float]) -> float:
    if len(series) < 2:
        return 0.0
    n = len(series)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(series) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, series))
    den = sum((x - mean_x) ** 2 for x in xs) or 1.0
    return num / den


def build_timeline(
    snapshots: list[Snapshot],
    horizon_months: int,
    velocity: float,
) -> list[TimelineFrame]:
    if not snapshots:
        return []
    churn = path_churn(snapshots)
    history: dict[str, list[NodeMetrics]] = {}
    last = snapshots[-1]
    last_cells = {c.node_id: c for c in node_metrics(last, churn)}
    for snap in snapshots:
        for cell in node_metrics(snap, churn):
            history.setdefault(cell.node_id, []).append(cell)

    marks = [0.0, 3.0, 8.0, 12.0, float(horizon_months)]
    marks = sorted({m for m in marks if m <= horizon_months})
    if horizon_months not in marks:
        marks.append(float(horizon_months))

    frames: list[TimelineFrame] = []
    for idx, months in enumerate(marks):
        cells: list[NodeMetrics] = []
        for nid, cell in last_cells.items():
            series_p = [c.pressure for c in history.get(nid, [cell])]
            series_m = [c.mass for c in history.get(nid, [cell])]
            series_v = [c.velocity for c in history.get(nid, [cell])]
            p0, m0, v0 = _smooth(series_p), _smooth(series_m), _smooth(series_v)
            # months → future samples via team velocity (commits/week)
            steps = months * (velocity * 4.3) / 1000.0
            pressure = max(0.0, p0 + _slope(series_p) * (1 + months / 6.0) + steps * 0.15)
            mass = max(0.1, m0 + _slope(series_m) * (months / 8.0))
            vel = max(0.02, v0 + _slope(series_v) * (months / 12.0))
            if cell.kind == "schema":
                pressure += months / 24.0 * 0.55
            if cell.kind == "contract" and cell.label.rstrip("/").endswith("s"):
                pressure += months / 24.0 * 0.4
            cells.append(
                cell.model_copy(
                    update={
                        "pressure": round(min(pressure, 3.5), 3),
                        "mass": round(mass, 3),
                        "velocity": round(vel, 3),
                        "momentum": round(mass * vel, 3),
                    }
                )
            )

        collisions = _collisions(cells, last, months)
        kind, narrative = _narrative(cells, collisions, months, detect_patterns(last))
        label = "now" if months == 0 else f"+{int(months)}mo"
        frames.append(
            TimelineFrame(
                t_index=idx,
                months_ahead=months,
                label=label,
                cells=cells,
                collisions=collisions,
                narrative=narrative,
                narrative_kind=kind,
            )
        )
    return frames


def _collisions(cells: list[NodeMetrics], snapshot: Snapshot, months: float) -> list[Collision]:
    schema = [c for c in cells if c.kind == "schema"]
    frontend = [c for c in cells if c.kind in {"module", "contract"} and c.lang == "typescript"]
    out: list[Collision] = []
    for s in schema:
        for f in frontend:
            intensity = (s.pressure + f.pressure) / 2.0 + months / 48.0
            if intensity < 0.7:
                continue
            out.append(
                Collision(
                    a=s.node_id,
                    b=f.node_id,
                    reason="schema_to_frontend",
                    intensity=round(min(intensity, 3.0), 3),
                )
            )
    return sorted(out, key=lambda c: c.intensity, reverse=True)[:8]


def _narrative(
    cells: list[NodeMetrics],
    collisions: list[Collision],
    months: float,
    labels: list[str],
) -> tuple[str, str]:
    avg_p = sum(c.pressure for c in cells) / max(len(cells), 1)
    if months >= 8 and collisions:
        top = collisions[0]
        return (
            "bottleneck",
            f"A schema change collides with frontend contracts around +{int(months)} months "
            f"(intensity {top.intensity}). Patterns: {', '.join(labels) or 'none'}.",
        )
    if avg_p > 1.1:
        return (
            "rising_pressure",
            f"Pressure is rising (mean {avg_p:.2f}) at +{int(months)} months. "
            "High-pressure zones are accumulating structural debt.",
        )
    return (
        "stable",
        f"Forecast at +{int(months)} months is stable (mean pressure {avg_p:.2f}).",
    )
