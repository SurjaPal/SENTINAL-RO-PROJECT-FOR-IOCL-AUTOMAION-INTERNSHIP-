-- Sentinel-RO — Module 4: Predictive Maintenance
--
-- This schema creates the anomalies table for persisting extrapolated machine learning forecasts.

CREATE TABLE IF NOT EXISTS anomalies (
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    sensor_type     TEXT NOT NULL,
    value           NUMERIC NOT NULL,
    reason          TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'warning'
);
SELECT create_hypertable('anomalies', by_range('time'), if_not_exists => TRUE);
