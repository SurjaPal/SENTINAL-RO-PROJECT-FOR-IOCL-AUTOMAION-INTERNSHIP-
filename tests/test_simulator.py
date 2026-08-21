"""
Unit tests for the simulator's pure generator functions — no MQTT broker
needed. Run with:  python -m unittest discover tests -v
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.telemetry_simulator import (  # noqa: E402
    RetailOutlet, make_demo_fleet, generate_atg_reading, generate_atg_alarm,
    generate_du_alarm, generate_psp_reading, generate_iot_health,
    generate_aip_snapshot, mqtt_topic, ATG_ALARM_TYPES, DU_ALARM_TYPES,
)


class TestFleetSetup(unittest.TestCase):
    def test_make_demo_fleet_creates_requested_count(self):
        fleet = make_demo_fleet(7)
        self.assertEqual(len(fleet), 7)

    def test_each_ro_has_unique_id(self):
        fleet = make_demo_fleet(10)
        ids = [ro.ro_id for ro in fleet]
        self.assertEqual(len(ids), len(set(ids)), "RO ids must be unique")

    def test_ro_defaults_populate_tanks_dus_iot(self):
        ro = RetailOutlet(ro_id="ROTEST", ro_name="Test", state="WB", region_tier="municipal")
        self.assertTrue(len(ro.tanks) >= 1)
        self.assertTrue(len(ro.dus) >= 1)
        self.assertTrue(len(ro.iot_devices) >= 1)
        # every tank should have a seeded baseline level
        for t in ro.tanks:
            self.assertIn(t, ro._tank_level_mm)


class TestAtgReading(unittest.TestCase):
    def setUp(self):
        self.ro = RetailOutlet(ro_id="RO1000", ro_name="Demo", state="WB", region_tier="municipal")
        self.tank = self.ro.tanks[0]

    def test_reading_has_all_schema_fields(self):
        reading = generate_atg_reading(self.ro, self.tank)
        for field in ("time", "ro_id", "tank_id", "product", "product_level_mm",
                      "water_level_mm", "volume_ltr", "temperature_c", "density"):
            self.assertIn(field, reading)

    def test_reading_is_json_serialisable(self):
        reading = generate_atg_reading(self.ro, self.tank)
        json.dumps(reading)  # raises if not serialisable

    def test_tank_level_drifts_downward_over_successive_readings(self):
        levels = []
        for _ in range(20):
            r = generate_atg_reading(self.ro, self.tank)
            levels.append(r["product_level_mm"])
        # a slow drain should trend down, not wander purely randomly
        self.assertLess(levels[-1], levels[0])

    def test_anomaly_flag_reduces_reported_volume(self):
        # run many trials since both paths use randomness — the anomaly
        # path should be lower on average, not necessarily every single time
        normal_vols = [generate_atg_reading(self.ro, self.tank, anomaly=False)["volume_ltr"]
                       for _ in range(30)]
        anomaly_vols = [generate_atg_reading(self.ro, self.tank, anomaly=True)["volume_ltr"]
                        for _ in range(30)]
        self.assertLess(sum(anomaly_vols) / len(anomaly_vols),
                         sum(normal_vols) / len(normal_vols))

    def test_level_never_goes_negative(self):
        for _ in range(500):
            r = generate_atg_reading(self.ro, self.tank)
            self.assertGreaterEqual(r["product_level_mm"], 0)


class TestAlarmGenerators(unittest.TestCase):
    def setUp(self):
        self.ro = RetailOutlet(ro_id="RO2000", ro_name="Demo", state="WB", region_tier="balance")

    def test_atg_alarm_type_is_always_valid(self):
        for _ in range(100):
            alarm = generate_atg_alarm(self.ro, self.ro.tanks[0])
            self.assertIn(alarm["alarm_type"], ATG_ALARM_TYPES)

    def test_du_alarm_type_is_always_valid(self):
        for _ in range(100):
            alarm = generate_du_alarm(self.ro, self.ro.dus[0])
            self.assertIn(alarm["alarm_type"], DU_ALARM_TYPES)

    def test_atg_alarm_severity_is_known_value(self):
        alarm = generate_atg_alarm(self.ro, self.ro.tanks[0])
        self.assertIn(alarm["severity"], {"info", "warning", "critical"})


class TestPspAndIot(unittest.TestCase):
    def setUp(self):
        self.ro = RetailOutlet(ro_id="RO3000", ro_name="Demo", state="WB", region_tier="ne_hill")

    def test_degraded_battery_is_lower_than_normal_on_average(self):
        normal = [generate_psp_reading(self.ro, degrade_battery=False)["battery_voltage"]
                  for _ in range(30)]
        degraded = [generate_psp_reading(self.ro, degrade_battery=True)["battery_voltage"]
                    for _ in range(30)]
        self.assertLess(sum(degraded) / len(degraded), sum(normal) / len(normal))

    def test_iot_health_connected_is_boolean(self):
        health = generate_iot_health(self.ro, self.ro.iot_devices[0])
        self.assertIsInstance(health["connected"], bool)
        self.assertIsInstance(health["tamper_detected"], bool)


class TestAipSnapshot(unittest.TestCase):
    def setUp(self):
        self.ro = RetailOutlet(ro_id="RO4000", ro_name="Demo", state="WB", region_tier="municipal")
        self.tank = self.ro.tanks[0]

    def test_normal_snapshot_has_small_variance(self):
        snap = generate_aip_snapshot(self.ro, self.tank, anomaly=False)
        variance = abs(snap["atg_stock_ltr"] - snap["nozzle_stock_ltr"])
        self.assertLessEqual(variance, 15.01)  # matches the +-15 noise band in the generator

    def test_anomalous_snapshot_has_large_variance(self):
        snap = generate_aip_snapshot(self.ro, self.tank, anomaly=True)
        variance = snap["atg_stock_ltr"] - snap["nozzle_stock_ltr"]
        self.assertGreaterEqual(variance, 150)  # matches the injected short-delivery gap


class TestMqttTopic(unittest.TestCase):
    def test_topic_without_sub_id(self):
        self.assertEqual(mqtt_topic("RO1000", "psp"), "iocl/RO1000/psp")

    def test_topic_with_sub_id(self):
        self.assertEqual(mqtt_topic("RO1000", "atg", "RO1000-TK1"), "iocl/RO1000/atg/RO1000-TK1")


if __name__ == "__main__":
    unittest.main()
