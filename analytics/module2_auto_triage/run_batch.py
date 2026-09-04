"""
Sentinel-RO — Module 2 (Week 7-8): live batch processing.

Reads unprocessed rows from `complaints`, builds a TelemetryContext for
each from the last few hours of alarms and Module 1/3 output, runs
classify_complaint + correlate, writes the result to triage_suggestions,
and marks the complaint processed. Same "not run against a live database
in this sandbox" caveat as every other run_batch.py in this project — see
README.md.

Run:
    python -m analytics.module2_auto_triage.run_batch
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from analytics.module2_auto_triage.complaint_classifier import classify_complaint  # noqa: E402
from analytics.module2_auto_triage.correlator import correlate, TelemetryContext  # noqa: E402
from analytics.module2_auto_triage.rag_repair import get_repair_instructions  # noqa: E402

INSERT_TRIAGE_SUGGESTION = (
    "INSERT INTO triage_suggestions "
    "(time, ro_id, complaint_id, complaint_category, suggested_root_cause, confidence, priority, evidence) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)
MARK_PROCESSED = "UPDATE complaints SET processed_at = now() WHERE complaint_id = %s"


def fetch_context(cursor, ro_id: str, complaint_time, window_hours: float) -> TelemetryContext:
    """The only part of this module that touches the database directly —
    everything downstream of this (classify_complaint, correlate) is pure
    and tested without one. Not exercised by unit tests; see
    tests/test_module2_auto_triage.py for what's tested instead."""
    cursor.execute(
        "SELECT alarm_type, time FROM atg_alarms WHERE ro_id=%s AND cleared_at IS NULL "
        "AND time >= %s - %s::interval",
        (ro_id, complaint_time, f"{window_hours} hours"),
    )
    open_atg = [{"alarm_type": r[0], "time": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        "SELECT alarm_type, time FROM du_alarms WHERE ro_id=%s AND cleared_at IS NULL "
        "AND time >= %s - %s::interval",
        (ro_id, complaint_time, f"{window_hours} hours"),
    )
    open_du = [{"alarm_type": r[0], "time": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        "SELECT link, time FROM connectivity_alarms WHERE ro_id=%s AND status='down' "
        "AND time >= %s - %s::interval",
        (ro_id, complaint_time, f"{window_hours} hours"),
    )
    open_conn = [{"link": r[0], "time": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        "SELECT risk_score, time FROM fault_alerts WHERE ro_id=%s AND flagged "
        "AND time >= %s - %s::interval",
        (ro_id, complaint_time, f"{window_hours} hours"),
    )
    fault_alerts = [{"risk_score": r[0], "time": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        "SELECT variance_ltr, anomaly_score, time FROM reconciliation_anomalies WHERE ro_id=%s AND flagged "
        "AND time >= %s - %s::interval",
        (ro_id, complaint_time, f"{window_hours} hours"),
    )
    anomalies = [{"variance_ltr": r[0], "anomaly_score": r[1], "time": r[2]} for r in cursor.fetchall()]

    return TelemetryContext(
        open_atg_alarms=open_atg, open_du_alarms=open_du, open_connectivity_alarms=open_conn,
        recent_fault_alerts=fault_alerts, recent_reconciliation_anomalies=anomalies,
    )


def run(dsn: str, window_hours: float) -> None:
    import psycopg2

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute("SELECT complaint_id, time, ro_id, raw_text FROM complaints WHERE processed_at IS NULL")
    pending = cursor.fetchall()
    if not pending:
        print("[module2] no unprocessed complaints.")
        return

    n_written = 0
    for complaint_id, complaint_time, ro_id, raw_text in pending:
        category = classify_complaint(raw_text)
        ctx = fetch_context(cursor, ro_id, complaint_time, window_hours)
        suggestion = correlate(category, ctx)

        repair_instructions = get_repair_instructions(suggestion.suggested_root_cause)
        enriched_root_cause = f"{suggestion.suggested_root_cause}\n\n🔧 REPAIR PLAN:\n{repair_instructions}"

        cursor.execute(INSERT_TRIAGE_SUGGESTION, (
            complaint_time, ro_id, complaint_id, suggestion.complaint_category,
            enriched_root_cause, suggestion.confidence, suggestion.priority, suggestion.evidence,
        ))
        cursor.execute(MARK_PROCESSED, (complaint_id,))
        n_written += 1

    print(f"[module2] processed {n_written} complaint(s).")


def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO Module 2 batch triage")
    parser.add_argument("--dsn", default=os.environ.get("SENTINEL_DB_DSN",
                         "dbname=sentinel user=sentinel password=sentinel host=localhost"))
    parser.add_argument("--window-hours", type=float, default=6,
                         help="how far back to look for corroborating telemetry")
    args = parser.parse_args()
    run(args.dsn, args.window_hours)


if __name__ == "__main__":
    main()
