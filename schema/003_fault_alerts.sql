-- Sentinel-RO — Week 5-6: Module 1 output table.
-- Run after 001_init.sql and 002_anomaly_watch.sql.

CREATE TABLE IF NOT EXISTS fault_alerts (
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    device_id       TEXT NOT NULL,          -- the PSP/battery unit this alert is about
    battery_voltage NUMERIC,
    detector        TEXT NOT NULL CHECK (detector IN ('trend_baseline', 'gradient_boosted')),
    risk_score      NUMERIC NOT NULL,       -- 0-1 for gradient_boosted; an unbounded severity score for trend_baseline
    flagged         BOOLEAN NOT NULL
);
SELECT create_hypertable('fault_alerts', by_range('time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_fault_alerts_flagged
    ON fault_alerts (ro_id, time DESC) WHERE flagged;
