"""
Sentinel-RO — Module 2 (Week 7-8): correlation engine.

Given a classified complaint and whatever Sentinel-RO already knows about
that RO from Modules 1 and 3 plus the raw alarm tables, suggests a root
cause, a confidence level, and a priority — this is the "pre-fill likely
root cause and route it" capability the Phase 11 tender's own ACC section
already asks vendors to build (see the project proposal, Section 2).

Rules are checked in priority order, strongest evidence first — an open
alarm of a matching type is about as close to certain as telemetry gets,
so it short-circuits everything else. Module 1/3 output are treated as
softer, "worth a look" signals, not confirmed causes, because they're
predictive/statistical flags, not hardware-confirmed faults.

Deliberately takes pre-fetched plain-Python data (TelemetryContext), not a
database connection — see run_batch.py for the actual TimescaleDB queries
that build one of these. Keeping the decision logic here pure is what
makes it testable without a live database, same pattern as every other
module in this project.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analytics.module2_auto_triage.complaint_classifier import UNCORROBORATED_CATEGORIES  # noqa: E402

# Matches the penalty comparison researched for the field-officer briefing:
# dispensing-affecting downtime is penalised at a materially higher rate
# (Rs.1,000/day/RO) than other equipment (Rs.300/day/RO) under the Phase 11
# tender — so a dispensing complaint should jump the queue.
DISPENSING_AFFECTING_CATEGORIES = {"no_dispensing"}

ALARM_TYPE_ROOT_CAUSE = {
    "atg_comm_failure": "ATG communication failure",
    "atg_struck": "ATG probe stuck / needs recalibration",
    "leak_detection": "Possible tank leak, flagged by ATG",
    "product_high": "Tank overfill alarm at ATG",
    "water_high": "High water level in tank",
    "pump_comm_failure": "DU/pump communication failure",
    "preset_validation_mismatch": "DU preset validation mismatch",
    "invoice_mismatch": "Invoice/stock mismatch at ATG",
}

# Categories worth cross-checking against a live Module 3 reconciliation flag.
RECONCILIATION_RELEVANT_CATEGORIES = {"price_mismatch", "no_dispensing", "unclassified"}
# Categories worth cross-checking against a live Module 1 fault-alert flag.
FAULT_ALERT_RELEVANT_CATEGORIES = {"no_dispensing", "power_issue"}


@dataclass
class TelemetryContext:
    """Pre-fetched, recent-window records for one RO. All plain dicts —
    whatever a psycopg2 cursor.fetchall()-plus-dict-conversion would hand
    back, deliberately, so nothing here needs a live database to test."""
    open_atg_alarms: list[dict] = field(default_factory=list)
    open_du_alarms: list[dict] = field(default_factory=list)
    open_connectivity_alarms: list[dict] = field(default_factory=list)
    recent_fault_alerts: list[dict] = field(default_factory=list)              # Module 1 output
    recent_reconciliation_anomalies: list[dict] = field(default_factory=list)  # Module 3 output


@dataclass
class TriageSuggestion:
    complaint_category: str
    suggested_root_cause: str
    confidence: str   # "high" | "medium" | "low"
    priority: str     # "urgent" | "normal"
    evidence: str


def _priority(category: str) -> str:
    return "urgent" if category in DISPENSING_AFFECTING_CATEGORIES else "normal"


def correlate(category: str, ctx: TelemetryContext) -> TriageSuggestion:
    priority = _priority(category)

    if category in UNCORROBORATED_CATEGORIES:
        return TriageSuggestion(
            category, "No telemetry source for this category yet", "low", priority,
            "Sentinel-RO does not ingest POS/ITPS telemetry yet — route for manual diagnosis.",
        )

    # Rule 1: a direct open alarm of a type consistent with an equipment complaint.
    for alarm in ctx.open_du_alarms + ctx.open_atg_alarms:
        cause = ALARM_TYPE_ROOT_CAUSE.get(alarm.get("alarm_type"))
        if cause:
            return TriageSuggestion(
                category, cause, "high", priority,
                f"Open {alarm['alarm_type']} alarm at {alarm.get('time')}",
            )

    # Rule 2: an open connectivity alarm explains almost any complaint category.
    if ctx.open_connectivity_alarms:
        alarm = ctx.open_connectivity_alarms[0]
        return TriageSuggestion(
            category, f"Connectivity loss to {alarm.get('link', 'server')}", "high", priority,
            f"Open connectivity alarm at {alarm.get('time')}",
        )

    # Rule 3: Module 1's predictive fault alert — softer than a hardware alarm.
    if category in FAULT_ALERT_RELEVANT_CATEGORIES and ctx.recent_fault_alerts:
        best = max(ctx.recent_fault_alerts, key=lambda f: f["risk_score"])
        return TriageSuggestion(
            category, "Likely PSP/battery-related power issue (predictive alert)", "medium", priority,
            f"Module 1 flagged risk_score={best['risk_score']:.2f} at {best.get('time')}",
        )

    # Rule 4: Module 3's reconciliation anomaly — also a soft signal.
    if category in RECONCILIATION_RELEVANT_CATEGORIES and ctx.recent_reconciliation_anomalies:
        best = max(ctx.recent_reconciliation_anomalies, key=lambda a: a["anomaly_score"])
        return TriageSuggestion(
            category, "Possible stock reconciliation issue, verify manually", "medium", priority,
            f"Module 3 flagged variance_ltr={best['variance_ltr']} at {best.get('time')}",
        )

    # Rule 5: nothing correlates — an honest miss beats a confident guess.
    return TriageSuggestion(
        category, "No matching telemetry signal", "low", priority,
        "Checked ATG/DU/connectivity alarms and Module 1/3 output — nothing correlates. "
        "Route for manual diagnosis.",
    )
