"""
Sentinel-RO — Module 3 (Week 3-4): feature engineering.

Turns raw aip_stock_snapshots-shaped rows into the features both detectors
in detectors.py score against. Pure pandas — no DB, no sklearn — so this
is trivially unit-testable on its own.
"""
from __future__ import annotations

import pandas as pd


def add_reconciliation_features(df: pd.DataFrame) -> pd.DataFrame:
    """Input columns required: time, ro_id, tank_id, atg_stock_ltr, nozzle_stock_ltr.
    (variance_ltr is computed here if not already present — TimescaleDB's
    generated column means it usually will be, when this reads from a real
    query, but synthetic test data may not have it.)

    Adds:
      variance_ltr        atg_stock - nozzle_stock (signed: positive = ATG
                           reports more than nozzles accounted for)
      variance_pct         variance_ltr as a fraction of atg_stock_ltr —
                           normalises across tanks of different sizes
      delta_variance_ltr   change in variance_ltr since this tank's
                           previous snapshot — catches a sudden jump even
                           if the absolute variance is still small
    """
    required = {"time", "ro_id", "tank_id", "atg_stock_ltr", "nozzle_stock_ltr"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"input is missing required column(s): {missing}")

    out = df.sort_values(["ro_id", "tank_id", "time"]).reset_index(drop=True).copy()

    if "variance_ltr" not in out.columns:
        out["variance_ltr"] = out["atg_stock_ltr"] - out["nozzle_stock_ltr"]

    # guard against divide-by-zero on an empty/draining tank
    safe_denominator = out["atg_stock_ltr"].where(out["atg_stock_ltr"] != 0, other=pd.NA)
    out["variance_pct"] = out["variance_ltr"] / safe_denominator

    out["delta_variance_ltr"] = (
        out.groupby(["ro_id", "tank_id"])["variance_ltr"].diff().fillna(0.0)
    )

    return out
