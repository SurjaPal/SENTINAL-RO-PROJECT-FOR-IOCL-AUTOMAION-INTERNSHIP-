"""
Sentinel-RO — Week 1-2: ingestion, path A (direct MQTT -> TimescaleDB).

This is the pragmatic starting point: subscribe to the simulator's MQTT
topics and write straight into TimescaleDB. No Kafka in between yet.

Why start here instead of with the Kafka-mediated pipeline from the
proposal: the proposal's own Feasibility section already flags that an
intern won't get production-scale infra on day one — this is the "smallest
thing that actually proves the schema and the pipeline work" version.
Once you need multiple independent consumers reading the same stream (e.g.
Module 1's scorer AND Module 3's anomaly watcher both reading fault-alert
events without re-subscribing to MQTT twice), that's the trigger to add
Kafka in the middle — see ingestion/kafka_pipeline/ for that version,
which follows the same structure.

Design note for testability: every function that turns an incoming message
dict into a database row is a *pure* function — no MQTT client, no DB
cursor. `tests/test_ingestion.py` exercises these directly against an
in-memory SQLite database, so the parsing/validation logic is verified even
without a live broker or Postgres instance. Swapping in psycopg2 in
production changes zero lines of business logic below.

Usage:
    pip install -r ../requirements.txt
    export SENTINEL_DB_DSN="dbname=sentinel user=sentinel password=sentinel host=localhost"
    python direct_mqtt_to_timescale.py --broker localhost
"""
from __future__ import annotations

import argparse
import json
import os

# ---------------------------------------------------------------------------
# Row-shaping functions: message dict -> ordered tuple matching an INSERT's
# column order. Pure and testable — see tests/test_ingestion.py.
# ---------------------------------------------------------------------------

INSERT_ATG_READING = (
    "INSERT INTO atg_readings "
    "(time, ro_id, tank_id, product, product_level_mm, water_level_mm, volume_ltr, temperature_c, density) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)


def row_from_atg_reading(msg: dict) -> tuple:
    required = ("time", "ro_id", "tank_id", "product", "product_level_mm",
                "water_level_mm", "volume_ltr")
    _assert_has(msg, required)
    return (
        msg["time"], msg["ro_id"], msg["tank_id"], msg["product"],
        msg["product_level_mm"], msg["water_level_mm"], msg["volume_ltr"],
        msg.get("temperature_c"), msg.get("density"),
    )


INSERT_ATG_ALARM = (
    "INSERT INTO atg_alarms (time, ro_id, tank_id, alarm_type, severity) "
    "VALUES (%s, %s, %s, %s, %s)"
)

_VALID_ATG_ALARM_TYPES = {
    "product_high", "water_high", "product_low", "atg_struck",
    "atg_comm_failure", "leak_detection", "receipt_in_progress", "invoice_mismatch",
}


def row_from_atg_alarm(msg: dict) -> tuple:
    _assert_has(msg, ("time", "ro_id", "tank_id", "alarm_type"))
    if msg["alarm_type"] not in _VALID_ATG_ALARM_TYPES:
        raise ValueError(f"unknown ATG alarm_type: {msg['alarm_type']!r}")
    return (msg["time"], msg["ro_id"], msg["tank_id"], msg["alarm_type"],
            msg.get("severity", "warning"))


INSERT_DU_ALARM = (
    "INSERT INTO du_alarms (time, ro_id, du_id, nozzle_id, alarm_type) "
    "VALUES (%s, %s, %s, %s, %s)"
)

_VALID_DU_ALARM_TYPES = {"pump_comm_failure", "preset_validation_mismatch"}


def row_from_du_alarm(msg: dict) -> tuple:
    _assert_has(msg, ("time", "ro_id", "du_id", "alarm_type"))
    if msg["alarm_type"] not in _VALID_DU_ALARM_TYPES:
        raise ValueError(f"unknown DU alarm_type: {msg['alarm_type']!r}")
    return (msg["time"], msg["ro_id"], msg["du_id"], msg.get("nozzle_id"), msg["alarm_type"])


INSERT_PSP_READING = (
    "INSERT INTO psp_parameters "
    "(time, ro_id, mains_status, voltage_v, frequency_hz, battery_voltage, "
    "battery_temp_c, charging_status, load_pct) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)


def row_from_psp_reading(msg: dict) -> tuple:
    _assert_has(msg, ("time", "ro_id"))
    return (
        msg["time"], msg["ro_id"], msg.get("mains_status"), msg.get("voltage_v"),
        msg.get("frequency_hz"), msg.get("battery_voltage"), msg.get("battery_temp_c"),
        msg.get("charging_status"), msg.get("load_pct"),
    )


INSERT_IOT_HEALTH = (
    "INSERT INTO iot_device_health "
    "(time, ro_id, device_id, device_type, temperature_c, connected, tamper_detected) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)


def row_from_iot_health(msg: dict) -> tuple:
    _assert_has(msg, ("time", "ro_id", "device_id", "connected"))
    return (
        msg["time"], msg["ro_id"], msg["device_id"], msg.get("device_type"),
        msg.get("temperature_c"), bool(msg["connected"]), bool(msg.get("tamper_detected", False)),
    )


INSERT_AIP_SNAPSHOT = (
    "INSERT INTO aip_stock_snapshots (time, ro_id, tank_id, atg_stock_ltr, nozzle_stock_ltr) "
    "VALUES (%s, %s, %s, %s, %s)"
)


def row_from_aip_snapshot(msg: dict) -> tuple:
    _assert_has(msg, ("time", "ro_id", "tank_id", "atg_stock_ltr", "nozzle_stock_ltr"))
    return (msg["time"], msg["ro_id"], msg["tank_id"], msg["atg_stock_ltr"], msg["nozzle_stock_ltr"])


def _assert_has(msg: dict, fields: tuple[str, ...]) -> None:
    missing = [f for f in fields if f not in msg]
    if missing:
        raise ValueError(f"message missing required field(s): {missing}")


# Maps an MQTT topic's category segment -> (row-shaper, insert SQL).
# Topic shape: iocl/{ro_id}/{category}/{sub_id}  (see simulator's mqtt_topic()).
TOPIC_HANDLERS = {
    "atg": (row_from_atg_reading, INSERT_ATG_READING),
    "atg_alarm": (row_from_atg_alarm, INSERT_ATG_ALARM),
    "du_alarm": (row_from_du_alarm, INSERT_DU_ALARM),
    "psp": (row_from_psp_reading, INSERT_PSP_READING),
    "iot": (row_from_iot_health, INSERT_IOT_HEALTH),
    "aip": (row_from_aip_snapshot, INSERT_AIP_SNAPSHOT),
}


def handle_message(cursor, topic: str, payload: bytes) -> str:
    """Parses one MQTT message and inserts it. Returns the category handled,
    for logging/metrics. Raises ValueError on a malformed/unroutable message
    — callers decide whether to log-and-skip or dead-letter it."""
    parts = topic.split("/")
    if len(parts) < 3 or parts[0] != "iocl":
        raise ValueError(f"unrecognised topic shape: {topic!r}")
    category = parts[2]
    if category not in TOPIC_HANDLERS:
        raise ValueError(f"no handler registered for category: {category!r}")

    shaper, sql = TOPIC_HANDLERS[category]
    msg = json.loads(payload)
    row = shaper(msg)
    cursor.execute(sql, row)
    return category


# ---------------------------------------------------------------------------
# Thin I/O layer — live broker + live DB. Not exercised by unit tests.
# ---------------------------------------------------------------------------

def run(broker: str, port: int, dsn: str) -> None:
    import paho.mqtt.client as mqtt
    import psycopg2

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cursor = conn.cursor()

    counts: dict[str, int] = {}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        print(f"[ingest] connected to broker (rc={reason_code}); subscribing to iocl/#")
        client.subscribe("iocl/#")

    def on_message(client, userdata, msg):
        try:
            category = handle_message(cursor, msg.topic, msg.payload)
            counts[category] = counts.get(category, 0) + 1
            if sum(counts.values()) % 50 == 0:
                print(f"[ingest] running totals: {counts}")
        except Exception as exc:  # noqa: BLE001 — log and keep consuming
            print(f"[ingest] WARN dropped message on {msg.topic}: {exc}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker, port, keepalive=60)
    client.loop_forever()


def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO direct MQTT -> TimescaleDB ingestion")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--dsn", default=os.environ.get("SENTINEL_DB_DSN",
                         "dbname=sentinel user=sentinel password=sentinel host=localhost"))
    args = parser.parse_args()
    run(args.broker, args.port, args.dsn)


if __name__ == "__main__":
    main()
