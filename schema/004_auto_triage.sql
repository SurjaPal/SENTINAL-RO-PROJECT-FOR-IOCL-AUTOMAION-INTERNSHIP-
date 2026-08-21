-- Sentinel-RO — Week 7-8: Module 2 tables.
-- Run after 001-003.

-- A staging table representing what would arrive from e-RACTS via a real
-- API/webhook integration in production. This project doesn't integrate
-- with the actual e-RACTS system — that's IOCL-internal infrastructure an
-- intern wouldn't have API access to build against — so this table is
-- Sentinel-RO's own inbound queue, filled by whatever front-door process
-- (a webhook receiver, a polling job against e-RACTS's API) is built when
-- this goes from prototype to pilot.
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id    TEXT PRIMARY KEY,
    time            TIMESTAMPTZ NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    raw_text        TEXT NOT NULL,
    processed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_complaints_unprocessed ON complaints (ro_id, time) WHERE processed_at IS NULL;

CREATE TABLE IF NOT EXISTS triage_suggestions (
    time                    TIMESTAMPTZ NOT NULL,
    ro_id                   TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    complaint_id            TEXT NOT NULL REFERENCES complaints(complaint_id),
    complaint_category      TEXT NOT NULL,
    suggested_root_cause    TEXT NOT NULL,
    confidence              TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    priority                TEXT NOT NULL CHECK (priority IN ('urgent', 'normal')),
    evidence                TEXT NOT NULL
);
SELECT create_hypertable('triage_suggestions', by_range('time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_triage_suggestions_urgent
    ON triage_suggestions (ro_id, time DESC) WHERE priority = 'urgent';
