from aether_sdk.pressure import pressure_band, pressure_color


def test_pressure_bands():
    assert pressure_band(0.2) == "calm"
    assert pressure_band(0.9) == "watch"
    assert pressure_band(1.8) == "high-pressure"
    assert pressure_color(1.8) == "#e05a4f"
