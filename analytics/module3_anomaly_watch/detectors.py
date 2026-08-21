"""
Sentinel-RO — Module 3 (Week 3-4): the two detectors.

Two detectors on purpose, matching the proposal's cold-start mitigation
(Feasibility section): "start with unsupervised/statistical control-chart
baselines... and use e-RACTS's own resolution records as weak labels... to
bootstrap supervised models over the first few months."

  StatisticalBaselineDetector — a rolling z-score per (ro_id, tank_id).
  Needs no fitting phase at all beyond the rolling window itself, so it's
  the one you can turn on from day one, before you have any history to
  train on.

  IsolationForestDetector — needs an explicit fit() on a window of mostly-
  normal history before it can score anything, but still needs no labels
  (it's unsupervised) — it just needs to have seen "normal" before it can
  recognise "not normal". Wrapped in a scikit-learn Pipeline with a
  StandardScaler, per the learning guide's note on combining feature
  scaling with a model as one reusable object.

Both expose the same output shape — a DataFrame with `anomaly_score`
(higher = more anomalous) and `flagged` (bool) columns added — so
run_batch.py and evaluate.py don't need to know which one they're calling.
"""
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = ["variance_ltr", "variance_pct", "delta_variance_ltr"]


class StatisticalBaselineDetector:
    """Rolling z-score on variance_ltr, computed independently per
    (ro_id, tank_id) so a naturally "leakier" tank doesn't skew the
    threshold for a tighter one."""

    def __init__(self, window: int = 20, min_periods: int = 8, z_threshold: float = 3.0):
        self.window = window
        self.min_periods = min_periods
        self.z_threshold = z_threshold

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """df must already have a `variance_ltr` column (see features.py).
        Rows before `min_periods` observations exist for their tank get
        rolling_std = NaN and are never flagged — there isn't enough
        history yet to say whether they're unusual."""
        out = df.sort_values(["ro_id", "tank_id", "time"]).reset_index(drop=True).copy()

        grouped = out.groupby(["ro_id", "tank_id"])["variance_ltr"]
        rolling_mean = grouped.transform(
            lambda s: s.shift(1).rolling(self.window, min_periods=self.min_periods).mean()
        )
        rolling_std = grouped.transform(
            lambda s: s.shift(1).rolling(self.window, min_periods=self.min_periods).std()
        )
        # shift(1): each row is compared against the window *before* it,
        # not including itself — otherwise a single huge outlier drags its
        # own mean/std toward itself and can mask its own anomaly.

        out["rolling_mean_variance"] = rolling_mean
        out["rolling_std_variance"] = rolling_std
        zscore = (out["variance_ltr"] - rolling_mean) / rolling_std.replace(0, pd.NA)
        out["anomaly_score"] = zscore.abs()
        out["flagged"] = out["anomaly_score"] >= self.z_threshold
        out["flagged"] = out["flagged"].fillna(False)
        return out


class IsolationForestDetector:
    """Multivariate anomaly detector over [variance_ltr, variance_pct,
    delta_variance_ltr]. Needs fit() called once on a window of
    (mostly-normal) history before score() will work."""

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("iforest", IsolationForest(contamination=contamination, random_state=random_state)),
        ])
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "IsolationForestDetector":
        X = df[FEATURE_COLUMNS]
        self.pipeline.fit(X)
        self._fitted = True
        return self

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("call fit() on a history window before score()")
        out = df.copy()
        X = out[FEATURE_COLUMNS]

        # IsolationForest.score_samples: HIGHER = more normal. Flip the sign
        # so anomaly_score follows the same "higher = more anomalous"
        # convention as StatisticalBaselineDetector, so callers can treat
        # either detector's output identically.
        raw = self.pipeline.named_steps["iforest"].score_samples(
            self.pipeline.named_steps["scaler"].transform(X)
        )
        out["anomaly_score"] = -raw
        out["flagged"] = self.pipeline.predict(X) == -1  # sklearn convention: -1 = outlier
        return out
