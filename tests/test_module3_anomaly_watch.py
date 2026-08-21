"""
Tests for Module 3 (Week 3-4). Unlike Week 1-2's tests, these run the
*actual* detection logic — scikit-learn, pandas, and scipy are all present
in this sandbox, so there's no SQLite-stand-in caveat needed here. What's
still not tested: run_batch.py's live psycopg2/TimescaleDB calls (no live
DB in this sandbox — see README) — rows_to_insert(), the pure function it
delegates to, is tested directly instead.

Run:  python -m unittest discover tests -v
"""
import random
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analytics.module3_anomaly_watch.features import add_reconciliation_features  # noqa: E402
from analytics.module3_anomaly_watch.detectors import (  # noqa: E402
    StatisticalBaselineDetector, IsolationForestDetector,
)
from analytics.module3_anomaly_watch.run_batch import rows_to_insert  # noqa: E402
from analytics.module3_anomaly_watch.evaluate import build_labeled_series, evaluate  # noqa: E402


def _toy_series(variances: list[float], ro_id="RO1", tank_id="TK1") -> pd.DataFrame:
    """Builds a minimal aip_stock_snapshots-shaped frame from a list of
    desired variance_ltr values, one snapshot per minute.

    atg_stock_ltr varies slightly (deterministically) rather than sitting
    at one fixed number — with a literally constant atg_stock,
    variance_pct becomes an exact scalar multiple of variance_ltr, which
    makes two of the three model features perfectly collinear. That's a
    degenerate case IsolationForest handles poorly (see
    test_fitted_on_normal_data_flags_a_clear_outlier's docstring for what
    that looked like in practice) and real telemetry never produces, since
    a real tank's level is never exactly constant between readings.
    """
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i, v in enumerate(variances):
        atg = 20000.0 + (i % 5) * 3.0  # small deterministic wobble, breaks exact collinearity
        rows.append({
            "time": base + timedelta(minutes=i),
            "ro_id": ro_id,
            "tank_id": tank_id,
            "atg_stock_ltr": atg,
            "nozzle_stock_ltr": atg - v,
        })
    return pd.DataFrame(rows)


class TestFeatures(unittest.TestCase):
    def test_variance_ltr_is_computed_correctly(self):
        df = _toy_series([10, -5, 0, 20])
        feats = add_reconciliation_features(df)
        self.assertListEqual(list(feats["variance_ltr"]), [10, -5, 0, 20])

    def test_variance_pct_normalises_by_atg_stock(self):
        df = _toy_series([200])
        feats = add_reconciliation_features(df)
        expected = 200 / feats.loc[0, "atg_stock_ltr"]  # read back rather than assume a fixed atg value
        self.assertAlmostEqual(feats.loc[0, "variance_pct"], expected)

    def test_delta_variance_is_zero_on_first_row_per_tank(self):
        df = _toy_series([10, 30, 15])
        feats = add_reconciliation_features(df)
        self.assertEqual(feats.loc[0, "delta_variance_ltr"], 0.0)
        self.assertEqual(feats.loc[1, "delta_variance_ltr"], 20.0)  # 30 - 10
        self.assertEqual(feats.loc[2, "delta_variance_ltr"], -15.0)  # 15 - 30

    def test_delta_variance_resets_per_tank(self):
        df = pd.concat([_toy_series([10, 20], tank_id="TK1"),
                         _toy_series([100, 90], tank_id="TK2")], ignore_index=True)
        feats = add_reconciliation_features(df)
        tk2_first = feats[feats["tank_id"] == "TK2"].iloc[0]
        self.assertEqual(tk2_first["delta_variance_ltr"], 0.0,
                          "TK2's first row must not diff against TK1's last row")

    def test_missing_required_column_raises(self):
        df = _toy_series([10]).drop(columns=["atg_stock_ltr"])
        with self.assertRaises(ValueError):
            add_reconciliation_features(df)


class TestStatisticalBaselineDetector(unittest.TestCase):
    def test_stable_series_is_not_flagged(self):
        # small noise around zero, no real anomaly
        variances = [1, -2, 0, 1, -1, 2, 0, -1, 1, 0] * 3
        df = add_reconciliation_features(_toy_series(variances))
        scored = StatisticalBaselineDetector(window=10, min_periods=8).score(df)
        self.assertFalse(scored["flagged"].any())

    def test_sharp_spike_after_stable_history_is_flagged(self):
        variances = [1, -2, 0, 1, -1, 2, 0, -1, 1, 0, 1, -1] + [300]  # one big spike at the end
        df = add_reconciliation_features(_toy_series(variances))
        scored = StatisticalBaselineDetector(window=10, min_periods=8).score(df)
        self.assertTrue(scored.iloc[-1]["flagged"])

    def test_early_rows_before_min_periods_are_never_flagged(self):
        # even a huge value on row 0 shouldn't be flagged — there's no
        # history yet to judge it against
        variances = [500, 500, 500]
        df = add_reconciliation_features(_toy_series(variances))
        scored = StatisticalBaselineDetector(window=10, min_periods=8).score(df)
        self.assertFalse(scored["flagged"].any())

    def test_outlier_does_not_mask_itself_via_shift(self):
        # the spike must not be included in its own rolling mean/std —
        # this is what the shift(1) in detectors.py guards against
        variances = [1, -1, 0, 1, -1, 0, 1, -1, 0] + [500]
        df = add_reconciliation_features(_toy_series(variances))
        scored = StatisticalBaselineDetector(window=9, min_periods=8).score(df)
        self.assertTrue(scored.iloc[-1]["flagged"],
                         "a spike must be judged against history BEFORE it, not including it")


class TestIsolationForestDetector(unittest.TestCase):
    def test_raises_if_scored_before_fit(self):
        df = add_reconciliation_features(_toy_series([1, 2, 3]))
        with self.assertRaises(RuntimeError):
            IsolationForestDetector().score(df)

    def test_fitted_on_normal_data_flags_a_clear_outlier(self):
        # Gaussian noise, not a tiny repeating integer pattern — a training
        # set with almost no spread taught IsolationForest a degenerate
        # decision boundary the first time this test was written (an
        # extreme point kept landing in the same "high" branch as the
        # sparse legitimate high-end training points instead of being
        # isolated from them; see build_labeled_series/evaluate.py, which
        # uses the real simulator's noise and scores perfectly, for the
        # realistic-data version of this same detector).
        random.seed(11)
        history = _toy_series([round(random.gauss(0, 5), 1) for _ in range(60)])
        live = _toy_series([1.0, 300.0, -2.0])  # one obvious outlier in the middle
        history_f = add_reconciliation_features(history)
        live_f = add_reconciliation_features(live)

        det = IsolationForestDetector(contamination=0.05).fit(history_f)
        scored = det.score(live_f)
        self.assertTrue(scored.iloc[1]["flagged"])
        self.assertGreater(scored.iloc[1]["anomaly_score"], scored.iloc[0]["anomaly_score"])
        self.assertGreater(scored.iloc[1]["anomaly_score"], scored.iloc[2]["anomaly_score"])

    def test_anomaly_score_convention_matches_statistical_detector(self):
        # both detectors must agree that higher score = more anomalous
        random.seed(12)
        history = _toy_series([round(random.gauss(0, 5), 1) for _ in range(60)])
        live = _toy_series([1.0, 250.0])
        history_f = add_reconciliation_features(history)
        live_f = add_reconciliation_features(live)
        scored = IsolationForestDetector(contamination=0.05).fit(history_f).score(live_f)
        self.assertGreater(scored.iloc[1]["anomaly_score"], scored.iloc[0]["anomaly_score"])


class TestRowsToInsert(unittest.TestCase):
    def test_only_flagged_rows_are_kept(self):
        df = pd.DataFrame([
            {"time": "t1", "ro_id": "RO1", "tank_id": "TK1", "variance_ltr": 5.0,
             "variance_pct": 0.01, "anomaly_score": 0.4, "flagged": False},
            {"time": "t2", "ro_id": "RO1", "tank_id": "TK1", "variance_ltr": 300.0,
             "variance_pct": 0.2, "anomaly_score": 0.9, "flagged": True},
        ])
        rows = rows_to_insert(df, "statistical_baseline")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "TK1")

    def test_had_matching_alarm_flag_is_set_correctly(self):
        df = pd.DataFrame([
            {"time": "t1", "ro_id": "RO1", "tank_id": "TK1", "variance_ltr": 300.0,
             "variance_pct": 0.2, "anomaly_score": 0.9, "flagged": True},
            {"time": "t2", "ro_id": "RO2", "tank_id": "TK9", "variance_ltr": 250.0,
             "variance_pct": 0.15, "anomaly_score": 0.85, "flagged": True},
        ])
        rows = rows_to_insert(df, "isolation_forest", alarm_times={("RO1", "TK1")})
        by_ro = {r[1]: r for r in rows}
        self.assertTrue(by_ro["RO1"][-1])   # RO1/TK1 has a matching alarm
        self.assertFalse(by_ro["RO2"][-1])  # RO2/TK9 does not


class TestEvaluationHarness(unittest.TestCase):
    """A slower, more end-to-end sanity check: both detectors should beat a
    trivial always-normal baseline on synthetic data with a real signal."""

    def test_build_labeled_series_produces_requested_row_count(self):
        df = build_labeled_series(50, 0.1, seed=1)
        self.assertEqual(len(df), 50)
        self.assertIn("true_anomaly", df.columns)

    def test_both_detectors_beat_zero_recall_on_synthetic_anomalies(self):
        results = evaluate(history_n=150, live_n=100, seed=3)
        for name, metrics in results.items():
            self.assertGreater(metrics["recall"], 0.0, f"{name} caught none of the injected anomalies")
            self.assertGreater(metrics["precision"], 0.5, f"{name} is mostly false alarms")


if __name__ == "__main__":
    unittest.main()
