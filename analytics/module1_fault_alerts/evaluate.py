"""
Sentinel-RO — Module 1 (Week 5-6): evaluation harness.

Builds a labeled fleet of synthetic devices — some healthy throughout
(negative controls a classifier needs to see, or it never learns what
"fine" looks like), some with a decline-to-critical arc at a random start
point and rate — trains GradientBoostedRiskDetector on one set of devices,
and evaluates both detectors on a *different* set of devices entirely.

That device-level split (not a time-based split like Module 3's) is
deliberate: the real question for a predictive-maintenance model isn't
"can it extrapolate this one battery's trend a bit further" (a rolling
average could do that), it's "has it learned what decline looks like in
general, well enough to catch it on hardware it has never seen." Testing
on held-out devices is the only way to actually check that.

Two kinds of metric, on purpose:
  - standard precision/recall/F1 against the lookahead label, so this is
    comparable to Module 3's evaluation report.
  - median lead time — for declining test devices only, how many readings
    of advance warning did each detector give before the device actually
    went critical. This is the number that matters for the pitch: "0.786
    F1" doesn't mean anything to a field officer, "caught it 23 readings
    before failure, on average" does.

Run:  python -m analytics.module1_fault_alerts.evaluate
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from analytics.module1_fault_alerts.battery_trajectory import (  # noqa: E402
    generate_battery_trajectory, add_lookahead_label,
)
from analytics.module1_fault_alerts.features import add_trend_features  # noqa: E402
from analytics.module1_fault_alerts.detectors import (  # noqa: E402
    TrendBaselineDetector, GradientBoostedRiskDetector,
)

DEFAULT_LOOKAHEAD_K = 15
DEFAULT_WINDOW = 10


def build_fleet(n_healthy: int, n_declining: int, n_readings: int = 150,
                 lookahead_k: int = DEFAULT_LOOKAHEAD_K, seed: int | None = None) -> pd.DataFrame:
    """n_readings should stay comfortably above ~150 (the default) unless
    you also lower the decline_rate range below — a device needs roughly
    2.1V / decline_rate readings after decline_start to actually reach
    critical_voltage, and at the slowest supported rate (0.02) that's
    ~105 readings on its own. decline_start is capped well before the end
    of the series specifically so every "declining" device has enough
    runway left to finish declining, rather than being cut off mid-decline
    and silently behaving like a healthy device for evaluation purposes."""
    rng = random.Random(seed)
    trajectories = []
    device_idx = 0
    min_runway = 110  # readings the slowest decline_rate (0.02) needs to reach critical
    latest_decline_start = max(5, n_readings - min_runway)

    for _ in range(n_healthy):
        df, critical_idx = generate_battery_trajectory(
            n_readings, decline_start_idx=None, seed=rng.randint(0, 1_000_000))
        df["device_id"] = f"DEV{device_idx}"
        df["critical_idx"] = critical_idx  # NaN/None for healthy devices
        trajectories.append(df)
        device_idx += 1

    for _ in range(n_declining):
        decline_start = rng.randint(5, latest_decline_start) if latest_decline_start > 5 else 5
        decline_rate = rng.uniform(0.02, 0.05)
        df, critical_idx = generate_battery_trajectory(
            n_readings, decline_start_idx=decline_start, decline_rate=decline_rate,
            seed=rng.randint(0, 1_000_000))
        df["device_id"] = f"DEV{device_idx}"
        df["critical_idx"] = critical_idx
        trajectories.append(df)
        device_idx += 1

    full = pd.concat(trajectories, ignore_index=True)
    # pandas 3.x's groupby.apply drops the grouping column from what it
    # hands back, so device_id survives more reliably built back up by
    # looping per device explicitly than by trying to reconstruct it from
    # a groupby result.
    labeled = pd.concat(
        [add_lookahead_label(full[full["device_id"] == dev_id], lookahead_k)
         for dev_id in full["device_id"].unique()],
        ignore_index=True,
    )
    return labeled


def _lead_times(scored: pd.DataFrame) -> dict:
    """For each device with a real critical_idx, find the first flagged
    reading and report critical_idx - first_flagged_idx (readings of
    advance warning). Devices never flagged before going critical count
    as missed, tracked separately rather than silently dropped from the
    average — an average that quietly excludes misses looks better than
    the detector actually is."""
    lead_times = []
    missed = 0
    declining_devices = scored[scored["critical_idx"].notna()]["device_id"].unique()

    for device_id in declining_devices:
        device_rows = scored[scored["device_id"] == device_id].sort_values("reading_idx")
        critical_idx = device_rows["critical_idx"].iloc[0]
        before_critical = device_rows[device_rows["reading_idx"] < critical_idx]
        flagged_before = before_critical[before_critical["flagged"]]
        if flagged_before.empty:
            missed += 1
        else:
            first_flag_idx = flagged_before["reading_idx"].min()
            lead_times.append(critical_idx - first_flag_idx)

    return {
        "n_declining_devices": len(declining_devices),
        "n_missed": missed,
        "n_caught": len(lead_times),
        "median_lead_time_readings": (pd.Series(lead_times).median() if lead_times else None),
        "min_lead_time_readings": (min(lead_times) if lead_times else None),
    }


def evaluate(n_train_healthy: int = 15, n_train_declining: int = 15,
             n_test_healthy: int = 10, n_test_declining: int = 10,
             seed: int = 7) -> dict:
    train = build_fleet(n_train_healthy, n_train_declining, seed=seed)
    test = build_fleet(n_test_healthy, n_test_declining, seed=seed + 1000)  # disjoint device ids by construction below

    # build_fleet numbers devices from 0 within each call, so train/test
    # device ids collide as strings — make test's ids unmistakably distinct
    # before concatenating anything or comparing device-level results.
    test["device_id"] = "TEST-" + test["device_id"]

    train_features = add_trend_features(train, window=DEFAULT_WINDOW)
    test_features = add_trend_features(test, window=DEFAULT_WINDOW)

    results = {}

    # --- TrendBaselineDetector: no fit phase, score test devices directly ---
    trend_scored = TrendBaselineDetector().score(test_features)
    results["trend_baseline"] = {
        **_classification_metrics(trend_scored),
        **_lead_times(trend_scored),
    }

    # --- GradientBoostedRiskDetector: fit on TRAIN devices, score TEST devices ---
    gbc = GradientBoostedRiskDetector().fit(train_features)
    gbc_scored = gbc.score(test_features)
    results["gradient_boosted"] = {
        **_classification_metrics(gbc_scored),
        **_lead_times(gbc_scored),
    }

    return results


def _classification_metrics(scored: pd.DataFrame) -> dict:
    has_history = scored["rolling_mean_voltage"].notna()
    evaluable = scored[has_history]
    y_true = evaluable["label_will_fail"].astype(bool)
    y_pred = evaluable["flagged"].astype(bool)
    return {
        "n_evaluable_rows": len(evaluable),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 3),
    }


def main():
    results = evaluate()
    print("Module 1 — evaluation on held-out TEST devices (never seen during training)\n")
    for name, metrics in results.items():
        print(f"{name}:")
        for k, v in metrics.items():
            print(f"    {k}: {v}")
        print()


if __name__ == "__main__":
    main()
