-- Sentinel-RO — Week 1-2: telemetry schema
--
-- Mirrors the field names and device categories from the Phase 11 tender's
-- Functional Design Specification (FDS) — see the project proposal, Section 4
-- ("Data fields already defined in the FDS that Sentinel-RO consumes").
--
-- Run against PostgreSQL 14+ with the TimescaleDB extension installed.
-- Local dev: the docker-compose.yml in this repo uses `timescale/timescaledb:latest-pg16`,
-- which already has the extension baked in.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- Reference table: one row per Retail Outlet.
-- region_tier drives the "allowable free time" penalty tiers from the tender
-- (see the field-officer briefing's penalty comparison) — kept here so later
-- weeks can join telemetry back to the tier a given RO falls under.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS retail_outlets (
    ro_id           TEXT PRIMARY KEY,
    ro_name         TEXT NOT NULL,
    state           TEXT NOT NULL,
    region_tier     TEXT NOT NULL DEFAULT 'within_100km'
                        CHECK (region_tier IN ('municipal', 'within_100km', 'balance', 'ne_hill')),
    onboarded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- ATG (Automatic Tank Gauge) — raw readings, captured ~every 60s per FDS §12.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atg_readings (
    time                TIMESTAMPTZ NOT NULL,
    ro_id               TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    tank_id             TEXT NOT NULL,
    product             TEXT NOT NULL,           -- MS / HSD / XP95 / ...
    product_level_mm    NUMERIC NOT NULL,
    water_level_mm      NUMERIC NOT NULL,
    volume_ltr          NUMERIC NOT NULL,
    temperature_c       NUMERIC,
    density              NUMERIC
);
SELECT create_hypertable('atg_readings', by_range('time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_atg_readings_ro_tank ON atg_readings (ro_id, tank_id, time DESC);

-- ---------------------------------------------------------------------------
-- ATG alarms — event-based. alarm_type values match the FDS §28 taxonomy
-- (the same list used in the field-officer briefing's alarm comparison).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atg_alarms (
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    tank_id         TEXT NOT NULL,
    alarm_type      TEXT NOT NULL CHECK (alarm_type IN (
                        'product_high', 'water_high', 'product_low', 'atg_struck',
                        'atg_comm_failure', 'leak_detection', 'receipt_in_progress',
                        'invoice_mismatch'
                    )),
    severity        TEXT NOT NULL DEFAULT 'warning' CHECK (severity IN ('info', 'warning', 'critical')),
    cleared_at      TIMESTAMPTZ
);
SELECT create_hypertable('atg_alarms', by_range('time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_atg_alarms_ro_open ON atg_alarms (ro_id, cleared_at) WHERE cleared_at IS NULL;

-- ---------------------------------------------------------------------------
-- DU (Dispensing Unit) alarms.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS du_alarms (
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    du_id           TEXT NOT NULL,
    nozzle_id       TEXT,
    alarm_type      TEXT NOT NULL CHECK (alarm_type IN (
                        'pump_comm_failure', 'preset_validation_mismatch'
                    )),
    cleared_at      TIMESTAMPTZ
);
SELECT create_hypertable('du_alarms', by_range('time'), if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- Connectivity alarms — the RO's link to the central (CROC) or vendor server.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS connectivity_alarms (
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    link            TEXT NOT NULL CHECK (link IN ('central_server', 'vendor_server')),
    status          TEXT NOT NULL CHECK (status IN ('down', 'degraded', 'restored'))
);
SELECT create_hypertable('connectivity_alarms', by_range('time'), if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- PSP (Power Supply / Backup Unit) parameters — periodic, per FDS §12.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS psp_parameters (
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    mains_status    TEXT CHECK (mains_status IN ('present', 'absent')),
    voltage_v       NUMERIC,
    frequency_hz    NUMERIC,
    battery_voltage NUMERIC,
    battery_temp_c  NUMERIC,
    charging_status TEXT CHECK (charging_status IN ('charging', 'full', 'fault')),
    load_pct        NUMERIC
);
SELECT create_hypertable('psp_parameters', by_range('time'), if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- IoT device health — the Type-1 gateway / Type-2 slave devices themselves.
-- This category didn't exist before Phase 11 (see the field-officer briefing).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS iot_device_health (
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    device_id       TEXT NOT NULL,
    device_type     TEXT CHECK (device_type IN ('type1_gateway', 'type2_slave')),
    temperature_c   NUMERIC,
    connected       BOOLEAN NOT NULL,
    tamper_detected BOOLEAN NOT NULL DEFAULT FALSE
);
SELECT create_hypertable('iot_device_health', by_range('time'), if_not_exists => TRUE);

-- ---------------------------------------------------------------------------
-- AIP — Auto Inventory Point stock snapshot, every 30 min per FDS §32.
-- This is the table Module 3 (Week 3-4) will run anomaly detection over.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aip_stock_snapshots (
    time                TIMESTAMPTZ NOT NULL,
    ro_id               TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    tank_id             TEXT NOT NULL,
    atg_stock_ltr       NUMERIC NOT NULL,   -- what the tank gauge reports
    nozzle_stock_ltr    NUMERIC NOT NULL,   -- reconstructed from totalizer deltas
    variance_ltr        NUMERIC GENERATED ALWAYS AS (atg_stock_ltr - nozzle_stock_ltr) STORED
);
SELECT create_hypertable('aip_stock_snapshots', by_range('time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_aip_ro_tank_time ON aip_stock_snapshots (ro_id, tank_id, time DESC);

-- ---------------------------------------------------------------------------
-- One example continuous aggregate (TimescaleDB feature — see Section 4 of
-- the learning guide). This is the kind of rollup Module 1's fault-alert
-- scoring will read from instead of recomputing over raw rows every time.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS psp_battery_hourly
WITH (timescaledb.continuous) AS
SELECT
    ro_id,
    time_bucket('1 hour', time) AS bucket,
    avg(battery_voltage)        AS avg_battery_voltage,
    min(battery_voltage)        AS min_battery_voltage,
    avg(battery_temp_c)         AS avg_battery_temp_c
FROM psp_parameters
GROUP BY ro_id, bucket
WITH NO DATA;
