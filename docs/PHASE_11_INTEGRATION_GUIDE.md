# Phase 11 Automaton Systems Integration Guide

This document details the exact steps required to transition Sentinel-RO from a simulated environment to a fully operational, live predictive maintenance model ingesting real-time data from **Phase 11 Automaton Systems** deployed at Retail Outlets (ROs).

## Architecture Overview

Currently, Sentinel-RO uses a `simulator` container to generate synthetic telemetry and push it to the local Mosquitto MQTT broker. 

To run on real data, the `simulator` is disabled, and the physical Phase 11 edge gateways (or Forecourt Controllers - FCCs) at the stations are configured to act as MQTT Publishers, beaming data directly into Sentinel-RO's ingestion pipeline.

---

## Step 1: Disable the Simulator

You must first stop the synthetic data generation to ensure it does not pollute the real production data.

1. Open `docker-compose.yml`.
2. Locate the `simulator:` service block.
3. Either delete the entire block, or comment it out entirely.
4. Restart the stack:
   ```bash
   docker compose down
   docker compose up -d --build
   ```

## Step 2: Secure the MQTT Broker for External Traffic

By default, the local Mosquitto broker does not have authentication enabled and is not exposed to the public internet securely. To accept data from Phase 11 hardware across a WAN/Internet:

1. **Expose Ports:** Ensure port `1883` (and ideally `8883` for TLS) is exposed on your production server's firewall.
2. **Enable TLS/SSL:** Edit `mosquitto.conf` to enforce encrypted connections (MQTTS). You will need to provision certificates (e.g., Let's Encrypt) for your server.
3. **Authentication:** Add username/password authentication to `mosquitto.conf` to ensure only authorized Phase 11 edge devices can publish.

## Step 3: Configure the Phase 11 Edge Gateway

The Phase 11 automation systems at the retail outlets must be configured to point to your new central Sentinel-RO server.

Access the Phase 11 administrative panel or edge gateway configuration (often via a local technician interface) and update the IoT/Cloud export settings:
*   **Broker URL:** `mqtt://<YOUR_SERVER_PUBLIC_IP>` (or `mqtts://` if using TLS).
*   **Port:** `1883` (or `8883`).
*   **Credentials:** The username and password you configured in Step 2.

## Step 4: Map Payload Topologies

Sentinel-RO's ingestion scripts (`ingestion/direct_mqtt_to_timescale.py` and `ingestion/bridge_mqtt_to_kafka.py`) expect data on specific topics in a specific JSON structure.

### Option A: Configure Phase 11 to Match Sentinel-RO
Configure the Phase 11 systems to publish to the following MQTT topics:
*   `iocl/{ro_id}/atg` (For tank levels, temperature)
*   `iocl/{ro_id}/psp` (For UPS/battery parameters)
*   `iocl/{ro_id}/iot` (For sensor health)
*   `iocl/{ro_id}/atg_alarm` (For critical ATGs alerts)

### Option B: Write an Ingestion Adapter (Recommended)
Legacy or proprietary Phase 11 systems often cannot have their output payload structure changed. If they publish in a proprietary format (e.g., XML or deeply nested JSON):

1. Open `ingestion/direct_mqtt_to_timescale.py`.
2. Locate the `on_message` callback function.
3. Write a transformation mapping to parse the incoming Phase 11 payload and map it to the dictionary shape expected by the `rows_to_insert()` functions.

**Example Adapter Logic:**
```python
def parse_phase_11_payload(raw_json):
    # Phase 11 might send {"station_code": "1001", "tank1_vol": 4500}
    # We map it to Sentinel-RO's format:
    return {
        "ro_id": f"RO{raw_json['station_code']}",
        "volume_ltr": raw_json['tank1_vol'],
        "temperature_c": raw_json.get('temp', 0.0)
    }
```

## Step 5: Verify Live Data Flow

Once the edge controllers are configured and the broker is secured, telemetry will immediately begin flowing into TimescaleDB.

To verify the integration is successful:
1. SSH into your Sentinel-RO server.
2. Query the live database:
   ```bash
   docker compose exec timescaledb psql -U sentinel -d sentinel -c "SELECT * FROM atg_readings ORDER BY time DESC LIMIT 5;"
   ```
3. Open the Sentinel-RO Web UI (`http://<YOUR_SERVER_IP>:8080`). You will see the live metrics updating directly from the physical retail outlets. 
4. The Analytics Engine (Predictive Faults & Anomaly Watch) will automatically begin running batch processing on this new real-world data without requiring any code changes.
