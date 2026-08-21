"""
Sentinel-RO — Week 1-2: telemetry simulator.

Generates synthetic ATG / DU / PSP / connectivity / IoT-health / AIP messages
that match the field names in schema/001_init.sql, and publishes them over
MQTT using the same topic layout CROC's real IoT devices would use.

This file is split deliberately:
  - the `generate_*` functions are pure (no I/O) so they can be unit-tested
    without a broker — see tests/test_simulator.py.
  - `run()` is the thin MQTT-publishing loop around them.

Intervals are compressed from the FDS's real cadence (ATG ~60s, AIP ~30min)
so a demo actually shows moving data within a minute or two. Real intervals
are kept as constants below so it's a one-line change to go back to them.

Usage:
    pip install -r ../requirements.txt
    python telemetry_simulator.py --broker localhost --ros 5
"""
from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

# --- Real-world cadence per the FDS (kept for reference / easy revert) -----
ATG_READING_INTERVAL_REAL_S = 60
AIP_SNAPSHOT_INTERVAL_REAL_S = 30 * 60

# --- Compressed cadence used by this simulator for local demos -------------
ATG_READING_INTERVAL_DEMO_S = 5
AIP_SNAPSHOT_INTERVAL_DEMO_S = 60

PRODUCTS = ["MS", "HSD"]
ATG_ALARM_TYPES = [
    "product_high", "water_high", "product_low", "atg_struck",
    "atg_comm_failure", "leak_detection", "receipt_in_progress", "invoice_mismatch",
]
DU_ALARM_TYPES = ["pump_comm_failure", "preset_validation_mismatch"]


@dataclass
class RetailOutlet:
    """A simulated RO: fixed set of tanks, DUs, IoT devices."""
    ro_id: str
    ro_name: str
    state: str
    region_tier: str
    tanks: list[str] = field(default_factory=list)
    dus: list[str] = field(default_factory=list)
    iot_devices: list[str] = field(default_factory=list)
    # slowly-drifting "true" state per tank, so readings look realistic
    # instead of pure noise — this is also what Module 3 (Week 3-4) needs:
    # a baseline that occasionally goes anomalous, not white noise.
    _tank_level_mm: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.tanks:
            self.tanks = [f"{self.ro_id}-TK1", f"{self.ro_id}-TK2"]
        if not self.dus:
            self.dus = [f"{self.ro_id}-DU1", f"{self.ro_id}-DU2", f"{self.ro_id}-DU3"]
        if not self.iot_devices:
            self.iot_devices = [f"{self.ro_id}-IOT-GW1"]
        if not self._tank_level_mm:
            self._tank_level_mm = {t: random.uniform(1200, 1800) for t in self.tanks}


def make_demo_fleet(n_ros: int) -> list[RetailOutlet]:
    """Builds a small fleet of simulated ROs. Deterministic-ish naming so
    output is easy to eyeball while testing."""
    states = ["West Bengal", "Jharkhand", "Odisha", "Bihar", "Assam"]
    tiers = ["municipal", "within_100km", "balance", "ne_hill"]
    fleet = []
    for i in range(n_ros):
        ro_id = f"RO{1000 + i}"
        fleet.append(RetailOutlet(
            ro_id=ro_id,
            ro_name=f"Sentinel Demo Outlet {i + 1}",
            state=states[i % len(states)],
            region_tier=tiers[i % len(tiers)],
        ))
    return fleet


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_atg_reading(ro: RetailOutlet, tank_id: str, *, anomaly: bool = False) -> dict:
    """One ATG reading. With anomaly=True, injects a reconciliation-relevant
    drift (used to give Module 3 something real to detect later)."""
    base_level = ro._tank_level_mm[tank_id]
    # small random walk so consecutive readings look continuous, not jumpy
    drift = random.uniform(-3, -0.5)  # tank slowly drains between fills
    new_level = max(50.0, base_level + drift)
    ro._tank_level_mm[tank_id] = new_level

    volume = round(new_level * 12.4, 1)  # toy mm->litre conversion for a demo tank geometry
    if anomaly:
        # simulate a short-delivery / meter-drift style discrepancy
        volume = round(volume * random.uniform(0.90, 0.95), 1)

    return {
        "time": _now_iso(),
        "ro_id": ro.ro_id,
        "tank_id": tank_id,
        "product": PRODUCTS[hash(tank_id) % len(PRODUCTS)],
        "product_level_mm": round(new_level, 1),
        "water_level_mm": round(random.uniform(0, 4), 1),
        "volume_ltr": volume,
        "temperature_c": round(random.uniform(24, 34), 1),
        "density": round(random.uniform(730, 840), 1),
    }


def generate_atg_alarm(ro: RetailOutlet, tank_id: str) -> dict:
    return {
        "time": _now_iso(),
        "ro_id": ro.ro_id,
        "tank_id": tank_id,
        "alarm_type": random.choice(ATG_ALARM_TYPES),
        "severity": random.choice(["info", "warning", "critical"]),
    }


def generate_du_alarm(ro: RetailOutlet, du_id: str) -> dict:
    return {
        "time": _now_iso(),
        "ro_id": ro.ro_id,
        "du_id": du_id,
        "nozzle_id": f"{du_id}-N1",
        "alarm_type": random.choice(DU_ALARM_TYPES),
    }


def generate_psp_reading(ro: RetailOutlet, *, degrade_battery: bool = False) -> dict:
    """degrade_battery=True simulates the slow voltage decline Module 1
    (Week 5-6) is meant to learn to spot before the hard 'battery low' alarm."""
    battery_voltage = round(random.uniform(11.5, 13.2), 2)
    if degrade_battery:
        battery_voltage = round(random.uniform(10.2, 11.0), 2)
    return {
        "time": _now_iso(),
        "ro_id": ro.ro_id,
        "mains_status": random.choices(["present", "absent"], weights=[97, 3])[0],
        "voltage_v": round(random.uniform(215, 235), 1),
        "frequency_hz": round(random.uniform(49.7, 50.3), 2),
        "battery_voltage": battery_voltage,
        "battery_temp_c": round(random.uniform(28, 45), 1),
        "charging_status": random.choices(["charging", "full", "fault"], weights=[60, 38, 2])[0],
        "load_pct": round(random.uniform(20, 85), 1),
    }


def generate_iot_health(ro: RetailOutlet, device_id: str) -> dict:
    return {
        "time": _now_iso(),
        "ro_id": ro.ro_id,
        "device_id": device_id,
        "device_type": "type1_gateway",
        "temperature_c": round(random.uniform(30, 55), 1),
        "connected": random.choices([True, False], weights=[98, 2])[0],
        "tamper_detected": random.choices([True, False], weights=[1, 999])[0],
    }


def generate_aip_snapshot(ro: RetailOutlet, tank_id: str, *, anomaly: bool = False) -> dict:
    """The reconciliation record — atg_stock vs nozzle_stock. This is the
    exact table Module 3 (Week 3-4) runs anomaly detection over."""
    atg_stock = round(ro._tank_level_mm[tank_id] * 12.4, 1)
    # normally these should nearly match; small honest noise either way
    nozzle_stock = round(atg_stock + random.uniform(-15, 15), 1)
    if anomaly:
        # a "short delivery" / pilferage-shaped gap, well outside normal noise
        nozzle_stock = round(atg_stock - random.uniform(150, 400), 1)
    return {
        "time": _now_iso(),
        "ro_id": ro.ro_id,
        "tank_id": tank_id,
        "atg_stock_ltr": atg_stock,
        "nozzle_stock_ltr": nozzle_stock,
    }


def mqtt_topic(ro_id: str, category: str, sub_id: str | None = None) -> str:
    """Matches the hierarchy from the learning guide's MQTT section:
    iocl/{ro_id}/{category}[/{sub_id}]"""
    parts = ["iocl", ro_id, category]
    if sub_id:
        parts.append(sub_id)
    return "/".join(parts)


def run(broker: str, port: int, n_ros: int, anomaly_rate: float) -> None:
    """The actual publishing loop. Imports paho-mqtt lazily so the pure
    generator functions above stay importable/testable without it installed."""
    import paho.mqtt.client as mqtt

    fleet = make_demo_fleet(n_ros)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(broker, port, keepalive=60)
    client.loop_start()

    print(f"[simulator] publishing for {n_ros} ROs to {broker}:{port} "
          f"(ATG every {ATG_READING_INTERVAL_DEMO_S}s, AIP every {AIP_SNAPSHOT_INTERVAL_DEMO_S}s, "
          f"anomaly_rate={anomaly_rate})")

    last_aip = 0.0
    try:
        while True:
            now = time.monotonic()
            for ro in fleet:
                for tank_id in ro.tanks:
                    reading = generate_atg_reading(ro, tank_id, anomaly=random.random() < anomaly_rate)
                    client.publish(mqtt_topic(ro.ro_id, "atg", tank_id), json.dumps(reading))

                    if random.random() < 0.02:
                        alarm = generate_atg_alarm(ro, tank_id)
                        client.publish(mqtt_topic(ro.ro_id, "atg_alarm", tank_id), json.dumps(alarm))

                for du_id in ro.dus:
                    if random.random() < 0.01:
                        alarm = generate_du_alarm(ro, du_id)
                        client.publish(mqtt_topic(ro.ro_id, "du_alarm", du_id), json.dumps(alarm))

                psp = generate_psp_reading(ro, degrade_battery=random.random() < anomaly_rate)
                client.publish(mqtt_topic(ro.ro_id, "psp"), json.dumps(psp))

                for device_id in ro.iot_devices:
                    health = generate_iot_health(ro, device_id)
                    client.publish(mqtt_topic(ro.ro_id, "iot", device_id), json.dumps(health))

                if now - last_aip >= AIP_SNAPSHOT_INTERVAL_DEMO_S:
                    for tank_id in ro.tanks:
                        snap = generate_aip_snapshot(ro, tank_id, anomaly=random.random() < anomaly_rate)
                        client.publish(mqtt_topic(ro.ro_id, "aip", tank_id), json.dumps(snap))

            if now - last_aip >= AIP_SNAPSHOT_INTERVAL_DEMO_S:
                last_aip = now

            time.sleep(ATG_READING_INTERVAL_DEMO_S)
    except KeyboardInterrupt:
        print("\n[simulator] stopping.")
    finally:
        client.loop_stop()
        client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO telemetry simulator")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--ros", type=int, default=5, help="number of simulated Retail Outlets")
    parser.add_argument("--anomaly-rate", type=float, default=0.03,
                         help="probability per reading of injecting a fault/anomaly, for Week 3-6 to detect")
    args = parser.parse_args()
    run(args.broker, args.port, args.ros, args.anomaly_rate)


if __name__ == "__main__":
    main()
