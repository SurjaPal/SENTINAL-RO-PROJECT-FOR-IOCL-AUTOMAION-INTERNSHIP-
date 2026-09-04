-- Sentinel-RO — Module 5: Automated Logistics
--
CREATE TABLE IF NOT EXISTS dispatch_tickets (
    time            TIMESTAMPTZ NOT NULL,
    ticket_id       TEXT NOT NULL,
    ro_id           TEXT NOT NULL REFERENCES retail_outlets(ro_id),
    part_name       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'DISPATCHED',
    UNIQUE (time, ticket_id)
);
SELECT create_hypertable('dispatch_tickets', by_range('time'), if_not_exists => TRUE);
