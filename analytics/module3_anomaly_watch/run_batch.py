"""
Sentinel-RO — Module 3 (Week 3-4): live batch scoring.

Reads recent aip_stock_snapshots from TimescaleDB, scores them with both
detectors, and writes flagged rows into reconciliation_anomalies.

Like Week 1-2's direct_mqtt_to_timescale.py, this is split into a testable
core (rows_to_insert — pure, given a scored DataFrame) and a thin DB-I/O
shell (run — not exercised by unit tests, needs a live TimescaleDB). See
tests/test_module3_anomaly_watch.py for what's actually verified, and
README.md for the same "what's tested vs not" caveat as Week 1-2 — this
script has NOT been run against a live database in this sandbox.

Run (needs a history window already in the DB — see README):
    python -m analytics.module3_anomaly_watch.run_batch --hours 6
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from analytics.module3_anomaly_watch.features import add_reconciliation_features  # noqa: E402
from analytics.module3_anomaly_watch.detectors import (  # noqa: E402
    StatisticalBaselineDetector, IsolationForestDetector,
)

INSERT_ANOMALY = (
    "INSERT INTO reconciliation_anomalies "
    "(time, ro_id, tank_id, variance_ltr, variance_pct, detector, anomaly_score, flagged, had_matching_alarm) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)


def rows_to_insert(scored_df: pd.DataFrame, detector_name: str, alarm_times: set[tuple] | None = None) -> list[tuple]:
    """Pure function: scored_df (output of a detector's .score()) -> list
    of tuples ready for INSERT_ANOMALY. Only flagged rows are kept — an
    unflagged row has nothing for the ACC/dealer to act on.

    alarm_times, if given, is a set of (ro_id, tank_id) pairs that already
    have an open ATG alarm around the same time — used to set
    had_matching_alarm so triage can tell "Module 3 caught something no
    alarm did" apart from "this just confirms an alarm we already have"."""
    alarm_times = alarm_times or set()
    rows = []
    for _, r in scored_df[scored_df["flagged"]].iterrows():
        had_alarm = (r["ro_id"], r["tank_id"]) in alarm_times
        rows.append((
            r["time"], r["ro_id"], r["tank_id"], float(r["variance_ltr"]),
            float(r["variance_pct"]) if pd.notna(r["variance_pct"]) else None,
            detector_name, float(r["anomaly_score"]), bool(r["flagged"]), had_alarm,
        ))
    return rows


def run(dsn: str, hours: int, history_hours: int, z_threshold: float, contamination: float) -> None:
    import psycopg2

    conn = psycopg2.connect(dsn)
    conn.autocommit = True

    history_df = pd.read_sql(
    """
    SELECT time, ro_id, tank_id, atg_stock_ltr, nozzle_stock_ltr, variance_ltr
    FROM aip_stock_snapshots
    WHERE time >= now() - (%(history_hours)s || ' hours')::interval
    """,
    conn,
    params={"history_hours": str(history_hours)},
)
    
    if history_df.empty:
        print("[module3] no AIP history found yet — let the simulator + ingestion run longer first.")
        return

    live_df = history_df[
        history_df["time"] >= history_df["time"].max() - pd.Timedelta(hours=hours)
    ].reset_index(drop=True)

    features_full = add_reconciliation_features(history_df)
    features_live = features_full[features_full["time"].isin(live_df["time"])].reset_index(drop=True)

    alarms_df = pd.read_sql(
    """
    SELECT DISTINCT ro_id, tank_id
    FROM atg_alarms
    WHERE cleared_at IS NULL
      AND time >= now() - (%(hours)s || ' hours')::interval
    """,
    conn,
    params={"hours": str(hours)},
)
    
    alarm_times = set(zip(alarms_df["ro_id"], alarms_df["tank_id"]))

    all_rows: list[tuple] = []

    stat_scored = StatisticalBaselineDetector(z_threshold=z_threshold).score(features_full)
    stat_scored_live = stat_scored[stat_scored["time"].isin(live_df["time"])]
    all_rows += rows_to_insert(stat_scored_live, "statistical_baseline", alarm_times)

    if len(features_full) - len(features_live) >= 30:  # enough history to fit on
        iforest = IsolationForestDetector(contamination=contamination)
        iforest.fit(features_full[~features_full["time"].isin(live_df["time"])])
        iforest_scored = iforest.score(features_live)
        all_rows += rows_to_insert(iforest_scored, "isolation_forest", alarm_times)
    else:
        print("[module3] not enough history yet to fit IsolationForest — statistical baseline only this run.")

    with conn.cursor() as cursor:
        cursor.executemany(INSERT_ANOMALY, all_rows)
    print(f"[module3] wrote {len(all_rows)} flagged anomaly row(s) to reconciliation_anomalies.")


def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO Module 3 batch scoring")
    parser.add_argument("--dsn", default=os.environ.get("SENTINEL_DB_DSN",
                         "dbname=sentinel user=sentinel password=sentinel host=localhost"))
    parser.add_argument("--hours", type=float, default=6, help="window to score and write results for")
    parser.add_argument("--history-hours", type=float, default=48, help="how far back to pull for context/fitting")
    parser.add_argument("--z-threshold", type=float, default=3.0)
    parser.add_argument("--contamination", type=float, default=0.03)
    args = parser.parse_args()
    run(args.dsn, args.hours, args.history_hours, args.z_threshold, args.contamination)


if __name__ == "__main__":
    main()
