"""
Sentinel-RO — Module 3 (Week 3-4): evaluation harness.

Builds a labeled synthetic dataset (reusing the Week 1-2 simulator's
generate_aip_snapshot, which already tags ground truth via its `anomaly=`
flag) and reports precision/recall/F1 for both detectors on a held-out
window. This is the "shadow mode" validation the proposal's risk table
calls for — run it whenever you change a detector's parameters, not just
once, and definitely before letting either detector auto-raise a ticket.

Two different train/test disciplines on purpose:
  - StatisticalBaselineDetector doesn't get a separate fit() at all — its
    "training" is just the rolling window of prior rows in the same
    series, computed with shift(1) so it never looks at itself. Evaluated
    on the live window only, but scored across the full history+live
    series so the live window's rolling stats have real history behind them.
  - IsolationForestDetector gets an explicit fit() on the history window
    ONLY, then scores the live window — a proper train/test split, since
    unlike the rolling detector it would otherwise leak live-window
    statistics into its own training.

Run:  python -m analytics.module3_anomaly_watch.evaluate
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from simulator.telemetry_simulator import (  # noqa: E402
    RetailOutlet, generate_atg_reading, generate_aip_snapshot,
)
from analytics.module3_anomaly_watch.features import add_reconciliation_features  # noqa: E402
from analytics.module3_anomaly_watch.detectors import (  # noqa: E402
    StatisticalBaselineDetector, IsolationForestDetector,
)


def build_labeled_series(n_snapshots: int, anomaly_rate: float, *, seed: int | None = None) -> pd.DataFrame:
    """One tank, a time-ordered sequence of AIP snapshots with ground-truth
    labels. Interleaves generate_atg_reading() calls between snapshots so
    the underlying tank level actually drifts, the way it does in the live
    simulator loop — otherwise atg_stock_ltr would sit artificially static."""
    if seed is not None:
        random.seed(seed)

    ro = RetailOutlet(ro_id="ROEVAL", ro_name="Eval Outlet", state="WB", region_tier="municipal")
    tank_id = ro.tanks[0]
    base_time = datetime.now(timezone.utc)

    rows = []
    for i in range(n_snapshots):
        for _ in range(10):  # let the tank level drift between snapshots, as in the live loop
            generate_atg_reading(ro, tank_id)
        is_anomaly = random.random() < anomaly_rate
        snap = generate_aip_snapshot(ro, tank_id, anomaly=is_anomaly)
        snap["time"] = base_time + timedelta(minutes=i)
        snap["true_anomaly"] = is_anomaly
        rows.append(snap)

    return pd.DataFrame(rows)


def evaluate(history_n: int = 300, live_n: int = 200,
             history_anomaly_rate: float = 0.02, live_anomaly_rate: float = 0.10,
             seed: int = 7) -> dict:
    history = build_labeled_series(history_n, history_anomaly_rate, seed=seed)
    live = build_labeled_series(live_n, live_anomaly_rate, seed=seed + 1)
    # shift the live window's clock so it comes chronologically after history
    live["time"] = live["time"] + (history["time"].max() - live["time"].min()) + timedelta(minutes=1)

    full = pd.concat([history, live], ignore_index=True)
    full_features = add_reconciliation_features(full)

    history_features = full_features.iloc[:history_n].reset_index(drop=True)
    live_features = full_features.iloc[history_n:].reset_index(drop=True)

    results = {}

    # --- Statistical baseline: score the whole series, evaluate on the live slice ---
    stat_detector = StatisticalBaselineDetector()
    stat_scored_full = stat_detector.score(full_features)
    stat_scored_live = stat_scored_full.iloc[history_n:].reset_index(drop=True)
    results["statistical_baseline"] = _score_metrics(stat_scored_live)

    # --- IsolationForest: fit on history only, evaluate on live only ---
    iforest_detector = IsolationForestDetector(contamination=max(history_anomaly_rate, 0.01))
    iforest_detector.fit(history_features)
    iforest_scored_live = iforest_detector.score(live_features)
    results["isolation_forest"] = _score_metrics(iforest_scored_live)

    return results


def _score_metrics(scored_df: pd.DataFrame) -> dict:
    y_true = scored_df["true_anomaly"].astype(bool)
    y_pred = scored_df["flagged"].astype(bool)
    return {
        "n_live_rows": len(scored_df),
        "n_true_anomalies": int(y_true.sum()),
        "n_flagged": int(y_pred.sum()),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 3),
    }


def main():
    results = evaluate()
    print("Module 3 — evaluation on held-out live window (labels from the simulator's `anomaly=` flag)\n")
    for name, metrics in results.items():
        print(f"{name}:")
        for k, v in metrics.items():
            print(f"    {k}: {v}")
        print()


if __name__ == "__main__":
    main()
