"""
Sentinel-RO — Module 2 (Week 7-8): evaluation.

There's no ML model here, so there's no precision/recall to report the way
Modules 1 and 3 do — this is a rule-based system, so what's worth
evaluating is whether the *rules themselves* behave as intended across a
representative set of scenarios. Think of this as a test suite that
reports a pass rate rather than a classifier being scored against labels;
it's a genuinely different kind of evaluation for a genuinely different
kind of module, not a lesser version of Module 1/3's evaluation.

Run:  python -m analytics.module2_auto_triage.evaluate
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from analytics.module2_auto_triage.complaint_classifier import classify_complaint  # noqa: E402
from analytics.module2_auto_triage.correlator import correlate, TelemetryContext  # noqa: E402


def build_scenarios() -> list[dict]:
    """Each scenario: a complaint's free text, the telemetry Sentinel-RO
    would have on hand for that RO at that moment, and what a correct
    triage suggestion should look like. Covers one scenario per
    correlation rule in correlator.py, in the same priority order, plus a
    couple of "nothing correlates" and "uncorroborated category" cases."""
    return [
        {
            "name": "direct DU alarm match",
            "text": "pump not working at nozzle 2",
            "ctx": TelemetryContext(open_du_alarms=[{"alarm_type": "pump_comm_failure", "time": "10:02"}]),
            "expect_category": "no_dispensing",
            "expect_confidence": "high",
            "expect_priority": "urgent",
            "expect_cause_contains": "DU/pump communication",
        },
        {
            "name": "direct ATG alarm match",
            "text": "fuel not coming from nozzle",
            "ctx": TelemetryContext(open_atg_alarms=[{"alarm_type": "atg_struck", "time": "09:40"}]),
            "expect_category": "no_dispensing",
            "expect_confidence": "high",
            "expect_priority": "urgent",
            "expect_cause_contains": "ATG probe stuck",
        },
        {
            "name": "connectivity alarm covers an otherwise-unexplained complaint",
            "text": "pump not working, dealer says whole system is down",
            "ctx": TelemetryContext(open_connectivity_alarms=[{"link": "central_server", "time": "08:15"}]),
            "expect_category": "no_dispensing",
            "expect_confidence": "high",
            "expect_priority": "urgent",
            "expect_cause_contains": "Connectivity loss",
        },
        {
            "name": "Module 1 fault alert backs up a power complaint",
            "text": "power cut at the outlet, generator not picking up",
            "ctx": TelemetryContext(recent_fault_alerts=[{"risk_score": 0.87, "time": "07:50"}]),
            "expect_category": "power_issue",
            "expect_confidence": "medium",
            "expect_priority": "normal",
            "expect_cause_contains": "PSP/battery",
        },
        {
            "name": "Module 3 anomaly backs up a price complaint",
            "text": "customer says rate wrong on the display",
            "ctx": TelemetryContext(recent_reconciliation_anomalies=[
                {"variance_ltr": 210.4, "anomaly_score": 0.81, "time": "11:05"}
            ]),
            "expect_category": "price_mismatch",
            "expect_confidence": "medium",
            "expect_priority": "normal",
            "expect_cause_contains": "reconciliation",
        },
        {
            "name": "no dispensing, genuinely nothing correlates",
            "text": "nozzle stopped working suddenly",
            "ctx": TelemetryContext(),
            "expect_category": "no_dispensing",
            "expect_confidence": "low",
            "expect_priority": "urgent",  # still urgent on category alone, even with no evidence
            "expect_cause_contains": "No matching telemetry",
        },
        {
            "name": "uncorroborated category — screen issue",
            "text": "console screen blank at the counter",
            "ctx": TelemetryContext(recent_fault_alerts=[{"risk_score": 0.9, "time": "12:00"}]),  # shouldn't matter
            "expect_category": "screen_issue",
            "expect_confidence": "low",
            "expect_priority": "normal",
            "expect_cause_contains": "No telemetry source",
        },
        {
            "name": "uncorroborated category — card payment",
            "text": "customer card declined at pump",
            "ctx": TelemetryContext(),
            "expect_category": "card_payment_issue",
            "expect_confidence": "low",
            "expect_priority": "normal",
            "expect_cause_contains": "No telemetry source",
        },
        {
            "name": "unclassified text still checks reconciliation",
            "text": "dealer called with a general complaint about outlet 4",
            "ctx": TelemetryContext(recent_reconciliation_anomalies=[
                {"variance_ltr": 300.0, "anomaly_score": 0.9, "time": "13:00"}
            ]),
            "expect_category": "unclassified",
            "expect_confidence": "medium",
            "expect_priority": "normal",
            "expect_cause_contains": "reconciliation",
        },
        {
            "name": "alarm evidence outranks a weaker Module 1/3 signal",
            "text": "power cut, pump also not dispensing",
            "ctx": TelemetryContext(
                open_du_alarms=[{"alarm_type": "pump_comm_failure", "time": "14:00"}],
                recent_fault_alerts=[{"risk_score": 0.6, "time": "13:55"}],
            ),
            "expect_category": "no_dispensing",  # "not dispensing" keyword wins classification (checked first)
            "expect_confidence": "high",
            "expect_priority": "urgent",
            "expect_cause_contains": "DU/pump communication",
        },
    ]


def evaluate() -> dict:
    scenarios = build_scenarios()
    results = []
    for scenario in scenarios:
        category = classify_complaint(scenario["text"])
        suggestion = correlate(category, scenario["ctx"])

        passed = (
            category == scenario["expect_category"]
            and suggestion.confidence == scenario["expect_confidence"]
            and suggestion.priority == scenario["expect_priority"]
            and scenario["expect_cause_contains"].lower() in suggestion.suggested_root_cause.lower()
        )
        results.append({"name": scenario["name"], "passed": passed, "suggestion": suggestion, "category": category})

    n_passed = sum(r["passed"] for r in results)
    return {
        "n_scenarios": len(results),
        "n_passed": n_passed,
        "pass_rate": round(n_passed / len(results), 3),
        "results": results,
    }


def main():
    report = evaluate()
    print(f"Module 2 — scenario evaluation: {report['n_passed']}/{report['n_scenarios']} passed "
          f"({report['pass_rate']:.0%})\n")
    for r in report["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        s = r["suggestion"]
        print(f"[{status}] {r['name']}")
        print(f"       category={r['category']!r} confidence={s.confidence!r} "
              f"priority={s.priority!r}")
        print(f"       cause: {s.suggested_root_cause}")
        print()


if __name__ == "__main__":
    main()
