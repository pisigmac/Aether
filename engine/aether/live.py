"""Compact reading shared by the desktop live bar and the IDE plugin."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aether.ir.models import ForecastBundle, NodeMetrics, TimelineFrame


def pressure_band(pressure: float) -> str:
    if pressure < 0.6:
        return "calm"
    if pressure < 1.2:
        return "watch"
    return "high-pressure"


def live_repo_path() -> Path:
    return Path.home() / ".aether" / "live-repo"


def livebar_pid_path() -> Path:
    return Path.home() / ".aether" / "livebar.pid"


def repo_basename(path: str) -> str:
    name = Path(path).name
    return name or path or "repo"


def _norm(path: str) -> str:
    text = path.strip().rstrip("/")
    if not text:
        return ""
    try:
        return str(Path(text).resolve())
    except OSError:
        return str(Path(text))


def pick_universe_id(rows: list[tuple[str, str]], repo: str) -> str:
    """Match a checkout to an ingested universe.

    An exact path wins. A directory name matches only when one universe uses it,
    so two clones that share a basename are left unmatched.
    """
    target = _norm(repo)
    if not target:
        return ""
    for universe_id, repo_path in rows:
        if _norm(repo_path) == target:
            return universe_id
    name = Path(target).name
    named = [universe_id for universe_id, repo_path in rows if Path(repo_path).name == name]
    if len(named) == 1:
        return named[0]
    return ""


def job_targets_repo(label: str, request_path: str, result_path: str, repo: str) -> bool:
    target = _norm(repo)
    if not target:
        return False
    name = Path(target).name
    for raw in (label, request_path, result_path):
        if not raw:
            continue
        if _norm(raw) == target:
            return True
        if name and Path(raw).name == name:
            return True
    return False


def blank(state: str, repo_path: str = "", **extra: object) -> dict:
    reading: dict = {
        "state": state,
        "repo": repo_basename(repo_path) if repo_path else "",
        "repo_path": repo_path,
        "universe_id": "",
        "percent": 0,
        "stage": "",
        "error": "",
        "frame": "",
        "path": "",
        "band": "",
        "pressure": None,
        "narrative": "",
        "heuristic": True,
        "neighbors": [],
    }
    reading.update(extra)
    return reading


def _frame_near_eight(bundle: "ForecastBundle") -> "TimelineFrame | None":
    best: TimelineFrame | None = None
    for frame in bundle.timeline:
        if best is None or abs(frame.months_ahead - 8) < abs(best.months_ahead - 8):
            best = frame
    return best


def _band(frame: "TimelineFrame", cell: "NodeMetrics") -> str:
    if any(cell.node_id in (hit.a, hit.b) for hit in frame.collisions):
        return "storm"
    return pressure_band(cell.pressure)


def forecast_reading(bundle: "ForecastBundle") -> dict:
    frame = _frame_near_eight(bundle)
    if frame is None or not frame.cells:
        return blank("missing", bundle.repo_path, universe_id=bundle.universe_id, heuristic=bundle.heuristic)
    ranked = sorted(frame.cells, key=lambda cell: cell.pressure, reverse=True)
    hottest = ranked[0]
    neighbors = [
        {
            "path": cell.path or cell.label,
            "band": _band(frame, cell),
            "pressure": round(cell.pressure, 2),
        }
        for cell in ranked[1:4]
    ]
    return blank(
        "forecast",
        bundle.repo_path,
        universe_id=bundle.universe_id,
        frame=frame.label,
        path=hottest.path or hottest.label,
        band=_band(frame, hottest),
        pressure=round(hottest.pressure, 2),
        narrative=frame.narrative,
        heuristic=bundle.heuristic,
        neighbors=neighbors,
    )


def headline(reading: dict) -> str:
    repo = reading.get("repo") or "repo"
    state = reading.get("state")
    if state == "ingesting":
        return f"{repo}  {reading.get('percent', 0)}%  {reading.get('stage') or 'Queued'}"
    if state == "error":
        return f"{repo}  ingest failed  {reading.get('error') or reading.get('stage') or ''}".rstrip()
    if state == "missing":
        return f"{repo}  no forecast yet"
    if state == "empty":
        return "Open a repo"
    pressure = reading.get("pressure")
    shown = f"{pressure:.2f}" if isinstance(pressure, (int, float)) else ""
    return f"{repo}  {reading.get('path') or ''}  {reading.get('band') or ''}  P {shown}  {reading.get('frame') or ''}".rstrip()
