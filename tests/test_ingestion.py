"""
Tests for the ingestion layer's message parsing/validation, plus one
end-to-end integration test against an in-memory SQLite database standing
in for TimescaleDB.

Why SQLite here: this sandbox's network policy blocked installing
mosquitto/postgresql/paho-mqtt during development, so a live Postgres
instance wasn't available to test against directly. SQLite ships with
Python and speaks close-enough SQL for INSERT/SELECT round-trips, so it's
used as a stand-in to prove the parsing -> insert -> query flow is sound.
It is NOT a substitute for actually running this against real TimescaleDB
(no hypertables, no generated columns the same way, `%s` vs `?`
placeholders) — treat test_end_to_end_insert_and_query below as evidence
the *logic* is right, and still smoke-test against the real
docker-compose stack before trusting this in anything real. See README.md.

Run with:  python -m unittest discover tests -v
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.direct_mqtt_to_timescale import (  # noqa: E402
    row_from_atg_reading, row_from_atg_alarm, row_from_du_alarm,
    row_from_psp_reading, row_from_iot_health, row_from_aip_snapshot,
    handle_message, TOPIC_HANDLERS,
)

from simulator.telemetry_simulator import (  # noqa: E402
    RetailOutlet, generate_atg_reading, generate_atg_alarm, generate_du_alarm,
    generate_psp_reading, generate_iot_health, generate_aip_snapshot, mqtt_topic,
)
import json  # noqa: E402


class TestRowShapers(unittest.TestCase):
    def setUp(self):
        self.ro = RetailOutlet(ro_id="RO1000", ro_name="Demo", state="WB", region_tier="municipal")
        self.tank = self.ro.tanks[0]

    def test_atg_reading_row_matches_column_order(self):
        msg = generate_atg_reading(self.ro, self.tank)
        row = row_from_atg_reading(msg)
        self.assertEqual(row[1], msg["ro_id"])
        self.assertEqual(row[2], msg["tank_id"])
        self.assertEqual(row[6], msg["volume_ltr"])

    def test_atg_reading_missing_field_raises(self):
        msg = generate_atg_reading(self.ro, self.tank)
        del msg["volume_ltr"]
        with self.assertRaises(ValueError):
            row_from_atg_reading(msg)

    def test_atg_alarm_rejects_unknown_alarm_type(self):
        msg = generate_atg_alarm(self.ro, self.tank)
        msg["alarm_type"] = "not_a_real_alarm"
        with self.assertRaises(ValueError):
            row_from_atg_alarm(msg)

    def test_du_alarm_rejects_unknown_alarm_type(self):
        msg = generate_du_alarm(self.ro, self.ro.dus[0])
        msg["alarm_type"] = "bogus"
        with self.assertRaises(ValueError):
            row_from_du_alarm(msg)

    def test_psp_reading_row_length_matches_columns(self):
        msg = generate_psp_reading(self.ro)
        row = row_from_psp_reading(msg)
        self.assertEqual(len(row), 9)

    def test_iot_health_coerces_connected_to_bool(self):
        msg = generate_iot_health(self.ro, self.ro.iot_devices[0])
        msg["connected"] = 1  # simulate a loose JSON payload (0/1 instead of bool)
        row = row_from_iot_health(msg)
        self.assertIsInstance(row[5], bool)

    def test_aip_snapshot_row_matches_column_order(self):
        msg = generate_aip_snapshot(self.ro, self.tank)
        row = row_from_aip_snapshot(msg)
        self.assertEqual(row[3], msg["atg_stock_ltr"])
        self.assertEqual(row[4], msg["nozzle_stock_ltr"])


class TestHandleMessageRouting(unittest.TestCase):
    """handle_message() parses the topic to pick a handler — test that
    routing logic against a fake cursor that just records what it was
    asked to execute, no real DB needed."""

    class _RecordingCursor:
        def __init__(self):
            self.calls = []

        def execute(self, sql, row):
            self.calls.append((sql, row))

    def setUp(self):
        self.ro = RetailOutlet(ro_id="RO5000", ro_name="Demo", state="WB", region_tier="balance")
        self.cursor = self._RecordingCursor()

    def test_routes_atg_topic_to_atg_handler(self):
        msg = generate_atg_reading(self.ro, self.ro.tanks[0])
        topic = mqtt_topic(self.ro.ro_id, "atg", self.ro.tanks[0])
        category = handle_message(self.cursor, topic, json.dumps(msg).encode())
        self.assertEqual(category, "atg")
        self.assertEqual(len(self.cursor.calls), 1)

    def test_unrecognised_category_raises(self):
        with self.assertRaises(ValueError):
            handle_message(self.cursor, "iocl/RO5000/not_a_category", b"{}")

    def test_malformed_topic_raises(self):
        with self.assertRaises(ValueError):
            handle_message(self.cursor, "not-even-shaped-right", b"{}")

    def test_all_topic_handlers_are_wired_for_every_generator(self):
        # guards against a schema/topic drift: every category the simulator
        # can emit must have a registered handler here.
        expected_categories = {"atg", "atg_alarm", "du_alarm", "psp", "iot", "aip"}
        self.assertEqual(set(TOPIC_HANDLERS.keys()), expected_categories)


class TestEndToEndAgainstSqlite(unittest.TestCase):
    """Full parse -> insert -> query round trip, using SQLite as a stand-in
    for TimescaleDB since no live Postgres was reachable in this sandbox.
    See the module docstring for the caveat on what this does and doesn't
    prove."""

    SQLITE_SCHEMA = """
        CREATE TABLE atg_readings (
            time TEXT, ro_id TEXT, tank_id TEXT, product TEXT,
            product_level_mm REAL, water_level_mm REAL, volume_ltr REAL,
            temperature_c REAL, density REAL
        );
        CREATE TABLE aip_stock_snapshots (
            time TEXT, ro_id TEXT, tank_id TEXT,
            atg_stock_ltr REAL, nozzle_stock_ltr REAL
        );
    """

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(self.SQLITE_SCHEMA)
        self.ro = RetailOutlet(ro_id="RO9000", ro_name="Demo", state="WB", region_tier="municipal")

    def tearDown(self):
        self.conn.close()

    def _sqlite_execute(self, sql_postgres_style: str, row: tuple):
        # psycopg2 uses %s placeholders; sqlite3 uses ? — swap for the test only.
        sql_sqlite_style = sql_postgres_style.replace("%s", "?")
        self.conn.execute(sql_sqlite_style, row)

    def test_atg_reading_round_trip(self):
        msg = generate_atg_reading(self.ro, self.ro.tanks[0])
        from ingestion.direct_mqtt_to_timescale import INSERT_ATG_READING
        row = row_from_atg_reading(msg)
        self._sqlite_execute(INSERT_ATG_READING, row)
        self.conn.commit()

        result = self.conn.execute(
            "SELECT ro_id, tank_id, volume_ltr FROM atg_readings"
        ).fetchone()
        self.assertEqual(result, (msg["ro_id"], msg["tank_id"], msg["volume_ltr"]))

    def test_aip_variance_is_queryable_after_insert(self):
        """This is the exact query shape Week 3-4's anomaly-watch module
        will run — proving the schema supports it end to end, even in
        SQLite, is a useful early signal."""
        from ingestion.direct_mqtt_to_timescale import INSERT_AIP_SNAPSHOT
        normal_msg = generate_aip_snapshot(self.ro, self.ro.tanks[0], anomaly=False)
        anomaly_msg = generate_aip_snapshot(self.ro, self.ro.tanks[0], anomaly=True)

        self._sqlite_execute(INSERT_AIP_SNAPSHOT, row_from_aip_snapshot(normal_msg))
        self._sqlite_execute(INSERT_AIP_SNAPSHOT, row_from_aip_snapshot(anomaly_msg))
        self.conn.commit()

        rows = self.conn.execute(
            "SELECT atg_stock_ltr - nozzle_stock_ltr AS variance FROM aip_stock_snapshots "
            "ORDER BY variance DESC"
        ).fetchall()
        # the anomalous row should show up as the larger variance
        self.assertGreater(rows[0][0], rows[1][0])
        self.assertGreaterEqual(rows[0][0], 150)


if __name__ == "__main__":
    unittest.main()
