"""
Sentinel-RO — Module 1 (Week 5-6): the two detectors.

Same two-tier pattern as Module 3, same reasoning (proposal's cold-start
mitigation): a zero-training rule you can turn on immediately, and a
model that needs history but gets better with it.

  TrendBaselineDetector — "is voltage declining AND already below a watch
  level." No fitting phase, same as Module 3's StatisticalBaselineDetector.

  GradientBoostedRiskDetector — a supervised classifier predicting
  "will this device hit critical within the next K readings," trained on
  labeled trajectories (battery_trajectory.add_lookahead_label). This is
  the one place Sentinel-RO uses a *supervised* model rather than a purely
  unsupervised one — labels here come from the simulator's ground truth
  during development; in production they'd come from e-RACTS resolution
  history, exactly as the proposal's Feasibility section describes.

  No StandardScaler in this one, unlike Module 3's IsolationForestDetector
  — tree-based models like GradientBoostingClassifier split on raw
  thresholds per feature, so scaling doesn't change what they learn. It's
  worth noticing the difference: reach for a scaler with distance-based
  models (Isolation Forest, k-NN, anything using StandardScaler-sensitive
  math), skip it for tree-based ones.
"""
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

FEATURE_COLUMNS = [
    "battery_voltage", "rolling_mean_voltage", "rolling_slope_voltage",
    "rolling_std_voltage", "battery_temp_c", "rolling_fault_rate",
]


class TrendBaselineDetector:
    """Flags a device as "at risk" when its rolling voltage trend is
    declining AND it has already dropped below a watch level — either
    condition alone is too noisy (a flat healthy battery has small random
    negative slopes constantly; a battery can dip briefly below the watch
    level from load noise without actually declining)."""

    def __init__(self, watch_voltage: float = 12.0, slope_threshold: float = -0.015):
        self.watch_voltage = watch_voltage
        self.slope_threshold = slope_threshold  # volts/reading; must be this negative or more

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """df must already have rolling_slope_voltage (see features.py).
        Rows with no rolling slope yet (not enough history) are never
        flagged, same "no history, no verdict" rule as Module 3."""
        out = df.copy()
        has_history = out["rolling_slope_voltage"].notna()
        declining = out["rolling_slope_voltage"] <= self.slope_threshold
        below_watch = out["battery_voltage"] <= self.watch_voltage

        out["flagged"] = has_history & declining & below_watch
        # a simple 0-1ish severity: how far below watch, scaled by how fast it's dropping
        out["anomaly_score"] = (
            (self.watch_voltage - out["battery_voltage"]).clip(lower=0)
            * out["rolling_slope_voltage"].abs().fillna(0)
        )
        return out


class GradientBoostedRiskDetector:
    """Supervised: predicts P(will hit critical within the lookahead
    window used to build its training labels). Needs fit() on labeled
    trajectories before score() will work."""

    def __init__(self, **gbc_kwargs):
        gbc_kwargs.setdefault("n_estimators", 100)
        gbc_kwargs.setdefault("max_depth", 3)
        gbc_kwargs.setdefault("random_state", 42)
        self.model = GradientBoostingClassifier(**gbc_kwargs)
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "GradientBoostedRiskDetector":
        """df must have FEATURE_COLUMNS and `label_will_fail`
        (see battery_trajectory.add_lookahead_label). Rows with missing
        rolling features (not enough history yet) are dropped before
        fitting — they'd just be NaN noise to the model."""
        clean = df.dropna(subset=FEATURE_COLUMNS)
        self.model.fit(clean[FEATURE_COLUMNS], clean["label_will_fail"])
        self._fitted = True
        return self

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("call fit() on labeled history before score()")
        out = df.copy()
        has_history = out[FEATURE_COLUMNS].notna().all(axis=1)

        out["anomaly_score"] = 0.0
        out["flagged"] = False
        if has_history.any():
            scoreable = out.loc[has_history, FEATURE_COLUMNS]
            risk = self.model.predict_proba(scoreable)[:, 1]  # P(label_will_fail == True)
            out.loc[has_history, "anomaly_score"] = risk
            out.loc[has_history, "flagged"] = risk >= 0.5
        return out
