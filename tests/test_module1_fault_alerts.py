"""
Tests for Module 1 (Week 5-6). Same situation as Module 3's tests: pandas
and scikit-learn are present in this sandbox, so this exercises the real
detection logic, not just data-shaping. What's not tested: run_batch.py's
live TimescaleDB calls (see README) — rows_to_insert() is tested directly.

Run:  python -m unittest discover tests -v
"""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analytics.module1_fault_alerts.battery_trajectory import (  # noqa: E402
    generate_battery_trajectory, add_lookahead_label,
)
from analytics.module1_fault_alerts.features import add_trend_features  # noqa: E402
from analytics.module1_fault_alerts.detectors import (  # noqa: E402
    TrendBaselineDetector, GradientBoostedRiskDetector,
)
from analytics.module1_fault_alerts.evaluate import build_fleet  # noqa: E402
from analytics.module1_fault_alerts.run_batch import rows_to_insert  # noqa: E402


class TestBatteryTrajectory(unittest.TestCase):
    def test_healthy_device_never_goes_critical(self):
        df, critical_idx = generate_battery_trajectory(100, decline_start_idx=None, seed=1)
        self.assertIsNone(critical_idx)
        self.assertFalse(df["is_critical"].any())

    def test_declining_device_eventually_goes_critical(self):
        df, critical_idx = generate_battery_trajectory(
            100, decline_start_idx=20, decline_rate=0.05, seed=1)
        self.assertIsNotNone(critical_idx)
        self.assertTrue(df.loc[critical_idx:, "is_critical"].all())
        self.assertFalse(df.loc[:critical_idx - 1, "is_critical"].any())

    def test_voltage_stable_before_decline_starts(self):
        df, _ = generate_battery_trajectory(100, decline_start_idx=50, decline_rate=0.05, seed=2)
        early = df.loc[:40, "battery_voltage"]
        # should stay in a tight band around the healthy baseline, not trend
        self.assertLess(early.std(), 0.5)

    def test_faster_decline_rate_reaches_critical_sooner(self):
        # rates chosen so BOTH reliably cross critical within 300 readings —
        # 0.005/reading needs ~420 readings to cover the 2.1V gap on its
        # own, so an earlier version of this test used a rate slow enough
        # that it legitimately never went critical in the test window,
        # which isn't "slower," it's "didn't finish," and the comparison
        # was meaningless (None isn't greater than or less than anything).
        _, slow_idx = generate_battery_trajectory(300, decline_start_idx=10, decline_rate=0.02, seed=3)
        _, fast_idx = generate_battery_trajectory(300, decline_start_idx=10, decline_rate=0.10, seed=3)
        self.assertIsNotNone(slow_idx)
        self.assertIsNotNone(fast_idx)
        self.assertLess(fast_idx, slow_idx)


class TestLookaheadLabel(unittest.TestCase):
    def test_label_true_within_window_before_critical(self):
        df, critical_idx = generate_battery_trajectory(100, decline_start_idx=20, decline_rate=0.05, seed=1)
        labeled = add_lookahead_label(df, lookahead_k=10)
        # the reading exactly 10 before critical should be labeled True
        self.assertTrue(labeled.loc[critical_idx - 10, "label_will_fail"])

    def test_label_false_well_before_the_window(self):
        df, critical_idx = generate_battery_trajectory(100, decline_start_idx=20, decline_rate=0.03, seed=1)
        labeled = add_lookahead_label(df, lookahead_k=5)
        far_before = max(0, critical_idx - 30)
        self.assertFalse(labeled.loc[far_before, "label_will_fail"])

    def test_healthy_device_never_labeled_true(self):
        df, _ = generate_battery_trajectory(100, decline_start_idx=None, seed=1)
        labeled = add_lookahead_label(df, lookahead_k=15)
        self.assertFalse(labeled["label_will_fail"].any())


class TestFeatures(unittest.TestCase):
    def test_missing_column_raises(self):
        with self.assertRaises(ValueError):
            add_trend_features(pd.DataFrame({"battery_voltage": [12.0, 12.1]}))

    def test_rolling_slope_is_negative_during_decline(self):
        df, _ = generate_battery_trajectory(60, decline_start_idx=10, decline_rate=0.05, seed=1)
        feats = add_trend_features(df, window=10, min_periods=5)
        late_slope = feats["rolling_slope_voltage"].iloc[-1]
        self.assertLess(late_slope, -0.01)

    def test_rolling_slope_near_zero_when_stable(self):
        df, _ = generate_battery_trajectory(60, decline_start_idx=None, seed=1)
        feats = add_trend_features(df, window=10, min_periods=5)
        stable_slope = feats["rolling_slope_voltage"].iloc[-1]
        self.assertLess(abs(stable_slope), 0.02)

    def test_early_rows_have_no_rolling_stats(self):
        df, _ = generate_battery_trajectory(60, decline_start_idx=30, decline_rate=0.03, seed=1)
        feats = add_trend_features(df, window=10, min_periods=5)
        self.assertTrue(feats["rolling_mean_voltage"].iloc[:4].isna().all())

    def test_device_id_keeps_rolling_stats_independent_per_device(self):
        a, _ = generate_battery_trajectory(30, decline_start_idx=None, seed=1)
        a["device_id"] = "A"
        b, _ = generate_battery_trajectory(30, decline_start_idx=5, decline_rate=0.08, seed=2)
        b["device_id"] = "B"
        combined = pd.concat([a, b], ignore_index=True)
        feats = add_trend_features(combined, window=10, min_periods=5)
        # device B's first few rows must not see NaN-avoiding history from device A
        b_first_rows = feats[feats["device_id"] == "B"].iloc[:4]
        self.assertTrue(b_first_rows["rolling_mean_voltage"].isna().all())


class TestTrendBaselineDetector(unittest.TestCase):
    def test_stable_device_not_flagged(self):
        df, _ = generate_battery_trajectory(60, decline_start_idx=None, seed=1)
        feats = add_trend_features(df, window=10, min_periods=5)
        scored = TrendBaselineDetector().score(feats)
        self.assertFalse(scored["flagged"].any())

    def test_clear_decline_eventually_flagged(self):
        df, critical_idx = generate_battery_trajectory(80, decline_start_idx=10, decline_rate=0.06, seed=1)
        feats = add_trend_features(df, window=10, min_periods=5)
        scored = TrendBaselineDetector().score(feats)
        flagged_before_critical = scored[(scored["reading_idx"] < critical_idx) & scored["flagged"]]
        self.assertFalse(flagged_before_critical.empty, "should catch the decline before it goes critical")


class TestGradientBoostedRiskDetector(unittest.TestCase):
    def test_raises_if_scored_before_fit(self):
        df, _ = generate_battery_trajectory(30, decline_start_idx=None, seed=1)
        feats = add_trend_features(df)
        with self.assertRaises(RuntimeError):
            GradientBoostedRiskDetector().score(feats)

    def test_fitted_model_scores_declining_device_higher_than_healthy(self):
        train = build_fleet(n_healthy=8, n_declining=8, n_readings=100, seed=42)
        train_feats = add_trend_features(train, window=10, min_periods=5)
        det = GradientBoostedRiskDetector().fit(train_feats)

        healthy_df, _ = generate_battery_trajectory(100, decline_start_idx=None, seed=999)
        healthy_df["device_id"] = "HOLDOUT-HEALTHY"
        declining_df, critical_idx = generate_battery_trajectory(
            100, decline_start_idx=40, decline_rate=0.05, seed=998)
        declining_df["device_id"] = "HOLDOUT-DECLINING"

        combined = pd.concat([healthy_df, declining_df], ignore_index=True)
        combined_feats = add_trend_features(combined, window=10, min_periods=5)
        scored = det.score(combined_feats)

        healthy_max_score = scored[scored["device_id"] == "HOLDOUT-HEALTHY"]["anomaly_score"].max()
        declining_near_critical = scored[
            (scored["device_id"] == "HOLDOUT-DECLINING") & (scored["reading_idx"] == critical_idx - 5)
        ]["anomaly_score"].iloc[0]
        self.assertGreater(declining_near_critical, healthy_max_score)


class TestRowsToInsert(unittest.TestCase):
    def test_only_flagged_rows_kept_and_shaped_correctly(self):
        df = pd.DataFrame([
            {"time": "t1", "ro_id": "RO1", "device_id": "PSP1", "anomaly_score": 0.1, "flagged": False},
            {"time": "t2", "ro_id": "RO1", "device_id": "PSP1", "anomaly_score": 0.8, "flagged": True},
        ])
        rows = rows_to_insert(df, "trend_baseline")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "PSP1")


class TestEvaluationHarness(unittest.TestCase):
    def test_build_fleet_produces_expected_device_count(self):
        fleet = build_fleet(n_healthy=3, n_declining=2, n_readings=50, seed=1)
        self.assertEqual(fleet["device_id"].nunique(), 5)

    def test_declining_devices_outnumber_by_request(self):
        # n_readings must leave enough room after decline_start for the
        # decline to actually finish — see build_fleet's docstring context;
        # 50 readings isn't enough headroom at the default decline rates
        # and every device just ends mid-decline, never reaching critical.
        fleet = build_fleet(n_healthy=3, n_declining=2, n_readings=150, seed=1)
        n_declining_actual = fleet.groupby("device_id")["critical_idx"].first().notna().sum()
        self.assertEqual(n_declining_actual, 2)


if __name__ == "__main__":
    unittest.main()
