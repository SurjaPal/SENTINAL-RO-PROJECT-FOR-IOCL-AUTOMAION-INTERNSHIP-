"""
Sentinel-RO — Module 1 (Week 5-6): feature engineering.

Unlike Module 3's features (point-in-time values), these are all *trend*
features over a rolling window — the whole premise of predictive
maintenance is that the shape of the last N readings matters more than
any single one.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "battery_voltage", "rolling_mean_voltage", "rolling_slope_voltage",
    "rolling_std_voltage", "battery_temp_c", "rolling_fault_rate",
]


def _rolling_slope(values: np.ndarray) -> float:
    """Least-squares slope of value-vs-reading-index within one window.
    Units: volts per reading — a slope of -0.03 means "losing about 0.03V
    every reading," which is exactly decline_rate in battery_trajectory.py
    when the model is looking at a genuine decline."""
    if len(values) < 3 or np.all(values == values[0]):
        return 0.0
    x = np.arange(len(values))
    return float(np.polyfit(x, values, 1)[0])


def add_trend_features(df: pd.DataFrame, window: int = 10, min_periods: int = 5) -> pd.DataFrame:
    """Input columns required: battery_voltage, battery_temp_c, charging_status.
    If a `device_id` column is present, rolling stats are computed
    independently per device (required whenever this is scoring more than
    one device's readings concatenated together — see evaluate.py)."""
    required = {"battery_voltage", "battery_temp_c", "charging_status"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"input is missing required column(s): {missing}")

    out = df.copy()
    group_key = out["device_id"] if "device_id" in out.columns else pd.Series(0, index=out.index)

    voltage_grouped = out.groupby(group_key)["battery_voltage"]
    out["rolling_mean_voltage"] = voltage_grouped.transform(
        lambda s: s.rolling(window, min_periods=min_periods).mean()
    )
    out["rolling_std_voltage"] = voltage_grouped.transform(
        lambda s: s.rolling(window, min_periods=min_periods).std()
    )
    out["rolling_slope_voltage"] = voltage_grouped.transform(
        lambda s: s.rolling(window, min_periods=min_periods).apply(_rolling_slope, raw=True)
    )

    is_fault = (out["charging_status"] == "fault").astype(float)
    out["rolling_fault_rate"] = is_fault.groupby(group_key).transform(
        lambda s: s.rolling(window, min_periods=min_periods).mean()
    )

    return out
