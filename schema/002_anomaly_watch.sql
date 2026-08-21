-- Sentinel-RO — Week 3-4: Module 3 output table.
-- Run after 001_init.sql. Auto-picked-up by docker-compose's
-- docker-entrypoint-initdb.d mount (files run in filename order).

CREATE TABLE IF NOT EXISTS reconciliation_anomalies (
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    tank_id         TEXT NOT NULL,
    variance_ltr    NUMERIC NOT NULL,
    variance_pct    NUMERIC,
    detector        TEXT NOT NULL CHECK (detector IN ('statistical_baseline', 'isolation_forest')),
    anomaly_score   NUMERIC NOT NULL,
    flagged         BOOLEAN NOT NULL,
    -- carried through for triage — was this an event e-RACTS already knows
    -- about (an ATG alarm at the same time), or a silent variance with no
    -- alarm attached? The second case is exactly what Module 3 exists for.
    had_matching_alarm BOOLEAN NOT NULL DEFAULT FALSE
);
SELECT create_hypertable('reconciliation_anomalies', by_range('time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_reconciliation_anomalies_flagged
    ON reconciliation_anomalies (ro_id, time DESC) WHERE flagged;
