"""
Sentinel-RO — Module 1 (Week 5-6): battery-decline trajectory generator.

Module 3's anomaly watch could reuse the Week 1-2 simulator's `anomaly=`
flag directly, because point-in-time anomalies are exactly what it
generates. Module 1 is a different kind of problem — "will this device
fail soon" needs a *trajectory* leading up to failure, not an instant
before/after flag, so this module gets its own generator rather than
stretching the Week 1-2 simulator to do something it wasn't built for.
(The Week 1-2 simulator's `degrade_battery` flag still exists and is fine
for what it does — giving the live demo occasional low-battery readings —
this is specifically for training/evaluating a model that needs to see
the *shape* of a decline, not just isolated low readings.)

Three phases per simulated device, matching how a real lead-acid/VRLA
backup battery actually degrades:
  1. stable    — voltage oscillates around a healthy baseline
  2. declining — voltage trends downward at some rate, plus noise
  3. critical  — voltage has crossed the failure threshold

`is_critical` marks phase 3. The whole point of Module 1 is to flag
*during phase 2*, before phase 3 (and the hard PSP alarm it would trigger
in the real system) ever happens.
"""
from __future__ import annotations

import random

import pandas as pd

HEALTHY_VOLTAGE = 12.6
CRITICAL_VOLTAGE = 10.5
NOISE_STD = 0.15


def generate_battery_trajectory(
    n_readings: int,
    decline_start_idx: int | None,
    decline_rate: float = 0.03,
    *,
    healthy_voltage: float = HEALTHY_VOLTAGE,
    critical_voltage: float = CRITICAL_VOLTAGE,
    noise_std: float = NOISE_STD,
    seed: int | None = None,
) -> tuple[pd.DataFrame, int | None]:
    """One device's battery_voltage over n_readings ticks.

    decline_start_idx=None means the device stays healthy the whole time
    (a negative-control trajectory — Module 1 needs plenty of these during
    training, or it never learns what "fine" looks like).

    Returns (dataframe, critical_idx) where critical_idx is the first
    reading index at which voltage crossed critical_voltage (None if it
    never did in this trajectory).
    """
    rng = random.Random(seed)
    voltages = []
    temps = []
    charging = []
    critical_idx = None

    for i in range(n_readings):
        if decline_start_idx is None or i < decline_start_idx:
            base = healthy_voltage
            temp_base = 32.0
            charge_weights = [70, 28, 2]  # charging, full, fault
        else:
            steps_declining = i - decline_start_idx
            base = healthy_voltage - decline_rate * steps_declining
            temp_base = 34.0 + 0.05 * steps_declining  # a stressed battery runs a little warmer
            charge_weights = [40, 20, 40]  # "fault" gets much more likely while declining

        v = round(base + rng.gauss(0, noise_std), 2)
        voltages.append(v)
        temps.append(round(temp_base + rng.gauss(0, 1.5), 1))
        charging.append(rng.choices(["charging", "full", "fault"], weights=charge_weights)[0])

        if critical_idx is None and v <= critical_voltage:
            critical_idx = i

    is_critical = [critical_idx is not None and i >= critical_idx for i in range(n_readings)]

    df = pd.DataFrame({
        "reading_idx": range(n_readings),
        "battery_voltage": voltages,
        "battery_temp_c": temps,
        "charging_status": charging,
        "is_critical": is_critical,
    })
    return df, critical_idx


def add_lookahead_label(df: pd.DataFrame, lookahead_k: int) -> pd.DataFrame:
    """Adds `label_will_fail`: True if `is_critical` is True at this
    reading or any of the next `lookahead_k` readings. This is the
    training target — "should a model have raised a flag here, given what
    happens over the following window."

    Must be called per-device — see features.py's grouped usage — a
    lookahead computed across multiple concatenated devices would leak
    device B's early readings into device A's label.
    """
    out = df.copy()
    # reversed rolling max over `is_critical`, looking forward instead of back
    out["label_will_fail"] = (
        out["is_critical"][::-1].rolling(lookahead_k + 1, min_periods=1).max()[::-1].astype(bool)
    )
    return out
