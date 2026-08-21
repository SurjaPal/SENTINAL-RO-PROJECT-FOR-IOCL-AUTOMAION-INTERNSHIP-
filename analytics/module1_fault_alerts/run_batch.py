"""
Sentinel-RO — Module 1 (Week 5-6): live batch scoring.

Reads recent psp_parameters from TimescaleDB, scores them with both
detectors, and writes flagged rows into fault_alerts. Same "not run
against a live database in this sandbox" caveat as Module 3 — see
README.md.

One schema adaptation worth flagging: Week 1-2's psp_parameters table has
one row per (time, ro_id) — it doesn't have a separate device_id column,
because that schema assumed one PSP/battery backup unit per RO. Module
1's analytics code (features.py, detectors.py) groups by `device_id`
because during development that's the natural key across many simulated
battery_trajectory.py devices. Here, where they meet, ro_id is aliased
to device_id — one Retail Outlet's PSP readings are "one device" for
this grouping. If a future tender phase gives ROs multiple independently
tracked backup units, this alias is the line to change.

Run:
    python -m analytics.module1_fault_alerts.run_batch --hours 6
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from analytics.module1_fault_alerts.features import add_trend_features  # noqa: E402
from analytics.module1_fault_alerts.detectors import (  # noqa: E402
    TrendBaselineDetector, GradientBoostedRiskDetector,
)
from analytics.module1_fault_alerts.evaluate import build_fleet  # noqa: E402

INSERT_FAULT_ALERT = (
    "INSERT INTO fault_alerts (time, ro_id, device_id, battery_voltage, detector, risk_score, flagged) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)


def rows_to_insert(scored_df: pd.DataFrame, detector_name: str) -> list[tuple]:
    """Pure function: scored df -> INSERT_FAULT_ALERT-shaped tuples, flagged rows only."""
    rows = []
    for _, r in scored_df[scored_df["flagged"]].iterrows():
        rows.append((
            r["time"], r["ro_id"], r["device_id"],
            float(r["battery_voltage"]) if pd.notna(r.get("battery_voltage")) else None,
            detector_name, float(r["anomaly_score"]), bool(r["flagged"]),
        ))
    return rows


def run(dsn: str, hours: float, history_hours: float, lookahead_readings: int) -> None:
    import psycopg2

    conn = psycopg2.connect(dsn)
    conn.autocommit = True

    history_df = pd.read_sql(
    """
    SELECT time, ro_id, battery_voltage, battery_temp_c, charging_status
    FROM psp_parameters
    WHERE time >= now() - (%(history_hours)s || ' hours')::interval
    """,
    conn,
    params={"history_hours": str(history_hours)},
)
    
    if history_df.empty:
        print("[module1] no PSP history found yet — let the simulator + ingestion run longer first.")
        return

    history_df["device_id"] = history_df["ro_id"]  # see module docstring
    history_df["time"] = pd.to_datetime(history_df["time"])
    live_cutoff = history_df["time"].max() - pd.Timedelta(hours=hours)

    features_full = add_trend_features(history_df)
    features_live = features_full[features_full["time"] >= live_cutoff].reset_index(drop=True)

    all_rows: list[tuple] = []

    trend_scored = TrendBaselineDetector().score(features_live)
    all_rows += rows_to_insert(trend_scored, "trend_baseline")

    n_history_rows = len(features_full) - len(features_live)
    if n_history_rows >= 200:  # enough history across enough readings to bother fitting a model
        # NOTE: this trains on synthetic fleet data, not real fault history,
        # because live e-RACTS-confirmed fault labels aren't available yet
        # (see the proposal's cold-start mitigation). Swap build_fleet() for
        # a real labeled dataset once enough e-RACTS-resolved PSP cases
        # exist to build one — that's the natural upgrade path here, not a
        # code change.
        print("[module1] fitting GradientBoostedRiskDetector on synthetic fleet data "
              "(no real fault history to train on yet — see docstring)")
        synthetic_train = build_fleet(n_healthy=15, n_declining=15, seed=0)
        synthetic_train_labeled = synthetic_train  # already labeled by build_fleet
        synthetic_train_feats = add_trend_features(synthetic_train_labeled)
        gbc = GradientBoostedRiskDetector().fit(synthetic_train_feats)
        gbc_scored = gbc.score(features_live)
        all_rows += rows_to_insert(gbc_scored, "gradient_boosted")
    else:
        print("[module1] not enough history yet — trend baseline only this run.")

    with conn.cursor() as cursor:
        cursor.executemany(INSERT_FAULT_ALERT, all_rows)
    print(f"[module1] wrote {len(all_rows)} flagged fault-alert row(s) to fault_alerts.")


def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO Module 1 batch scoring")
    parser.add_argument("--dsn", default=os.environ.get("SENTINEL_DB_DSN",
                         "dbname=sentinel user=sentinel password=sentinel host=localhost"))
    parser.add_argument("--hours", type=float, default=6, help="window to score and write results for")
    parser.add_argument("--history-hours", type=float, default=72, help="how far back to pull for rolling context")
    parser.add_argument("--lookahead-readings", type=int, default=15)
    args = parser.parse_args()
    run(args.dsn, args.hours, args.history_hours, args.lookahead_readings)


if __name__ == "__main__":
    main()
