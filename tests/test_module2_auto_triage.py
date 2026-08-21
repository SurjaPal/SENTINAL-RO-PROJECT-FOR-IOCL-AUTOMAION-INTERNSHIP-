"""
Tests for Module 2 (Week 7-8). classify_complaint and correlate are both
pure, so this is fully exercised with no database or ML library needed —
the closest thing to a "free lunch" of the four modules, testing-wise.

Run:  python -m unittest discover tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytics.module2_auto_triage.complaint_classifier import (  # noqa: E402
    classify_complaint, UNCORROBORATED_CATEGORIES, CATEGORY_KEYWORDS,
)
from analytics.module2_auto_triage.correlator import correlate, TelemetryContext, _priority  # noqa: E402
from analytics.module2_auto_triage.evaluate import build_scenarios, evaluate  # noqa: E402


class TestClassifyComplaint(unittest.TestCase):
    def test_no_dispensing_keyword(self):
        self.assertEqual(classify_complaint("the pump is not dispensing fuel"), "no_dispensing")

    def test_power_issue_keyword(self):
        self.assertEqual(classify_complaint("there was a power cut this morning"), "power_issue")

    def test_price_mismatch_keyword(self):
        self.assertEqual(classify_complaint("customer says the rate wrong on display"), "price_mismatch")

    def test_case_insensitive(self):
        self.assertEqual(classify_complaint("PUMP NOT WORKING"), "no_dispensing")

    def test_unclassified_when_nothing_matches(self):
        self.assertEqual(classify_complaint("dealer called to say hello"), "unclassified")

    def test_every_category_has_at_least_one_keyword(self):
        for category, keywords in CATEGORY_KEYWORDS.items():
            self.assertGreater(len(keywords), 0, f"{category} has no keywords defined")

    def test_first_matching_category_wins_priority_order(self):
        # "not dispensing" should win over any coincidental power_issue wording
        text = "power seems fine but pump not working"
        self.assertEqual(classify_complaint(text), "no_dispensing")


class TestPriority(unittest.TestCase):
    def test_no_dispensing_is_urgent(self):
        self.assertEqual(_priority("no_dispensing"), "urgent")

    def test_other_categories_are_normal(self):
        for category in ["power_issue", "price_mismatch", "screen_issue", "card_payment_issue", "unclassified"]:
            self.assertEqual(_priority(category), "normal")


class TestCorrelate(unittest.TestCase):
    def test_uncorroborated_category_always_low_confidence(self):
        for category in UNCORROBORATED_CATEGORIES:
            ctx = TelemetryContext(open_du_alarms=[{"alarm_type": "pump_comm_failure", "time": "t"}])
            suggestion = correlate(category, ctx)
            self.assertEqual(suggestion.confidence, "low",
                              "an uncorroborated category must stay low-confidence even with unrelated alarms present")

    def test_open_du_alarm_beats_fault_alert(self):
        ctx = TelemetryContext(
            open_du_alarms=[{"alarm_type": "pump_comm_failure", "time": "t1"}],
            recent_fault_alerts=[{"risk_score": 0.99, "time": "t0"}],
        )
        suggestion = correlate("no_dispensing", ctx)
        self.assertEqual(suggestion.confidence, "high")
        self.assertIn("DU/pump communication", suggestion.suggested_root_cause)

    def test_unknown_alarm_type_does_not_crash_and_falls_through(self):
        ctx = TelemetryContext(open_du_alarms=[{"alarm_type": "some_future_alarm_type", "time": "t"}])
        suggestion = correlate("no_dispensing", ctx)
        # not in ALARM_TYPE_ROOT_CAUSE, so it should fall through to a lower-confidence rule
        self.assertNotEqual(suggestion.confidence, "high")

    def test_no_evidence_at_all_is_low_confidence_honest_miss(self):
        suggestion = correlate("no_dispensing", TelemetryContext())
        self.assertEqual(suggestion.confidence, "low")
        self.assertIn("No matching telemetry", suggestion.suggested_root_cause)

    def test_fault_alert_only_applies_to_relevant_categories(self):
        # a price_mismatch complaint shouldn't get a battery-related suggestion
        ctx = TelemetryContext(recent_fault_alerts=[{"risk_score": 0.95, "time": "t"}])
        suggestion = correlate("price_mismatch", ctx)
        self.assertNotIn("battery", suggestion.suggested_root_cause.lower())

    def test_picks_highest_scoring_fault_alert_when_several_present(self):
        ctx = TelemetryContext(recent_fault_alerts=[
            {"risk_score": 0.2, "time": "t1"}, {"risk_score": 0.91, "time": "t2"}, {"risk_score": 0.5, "time": "t3"},
        ])
        suggestion = correlate("power_issue", ctx)
        self.assertIn("0.91", suggestion.evidence)


class TestScenarioEvaluation(unittest.TestCase):
    def test_all_scenarios_pass(self):
        report = evaluate()
        failed = [r["name"] for r in report["results"] if not r["passed"]]
        self.assertEqual(failed, [], f"scenario(s) failed: {failed}")

    def test_scenarios_cover_every_confidence_level(self):
        scenarios = build_scenarios()
        confidences = {s["expect_confidence"] for s in scenarios}
        self.assertEqual(confidences, {"high", "medium", "low"})

    def test_scenarios_cover_every_correlation_rule(self):
        # sanity check on the test design itself, not the code: are we
        # actually exercising every rule in correlator.py, not just some of them
        scenarios = build_scenarios()
        causes = " ".join(s["expect_cause_contains"] for s in scenarios)
        for expected_fragment in ["communication", "Connectivity loss", "PSP/battery",
                                   "reconciliation", "No matching telemetry", "No telemetry source"]:
            self.assertIn(expected_fragment, causes)


if __name__ == "__main__":
    unittest.main()
