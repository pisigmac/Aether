from __future__ import annotations

from typing import Literal

Band = Literal["calm", "watch", "high-pressure"]


def pressure_band(pressure: float) -> Band:
    if pressure < 0.6:
        return "calm"
    if pressure < 1.2:
        return "watch"
    return "high-pressure"


def pressure_color(pressure: float) -> str:
    if pressure < 0.6:
        return "#3d9ee0"
    if pressure < 1.2:
        return "#d4a017"
    return "#e05a4f"
