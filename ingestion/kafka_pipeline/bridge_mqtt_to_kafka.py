"""
Sentinel-RO — ingestion, path B, stage 1: MQTT -> Kafka bridge.

This plays the role "Kafka Connect (read-only consumer group)" plays in the
proposal's tech stack. A real deployment would likely use Kafka Connect's
MQTT source connector directly rather than a hand-rolled bridge like this
one — but for local dev, this ~40-line script is a lot easier to run than
standing up a full Kafka Connect worker, and it does the same job: take
messages off MQTT topics and land them durably on Kafka topics so more than
one downstream consumer (Module 1's scorer, Module 3's anomaly watcher,
Grafana's live feed) can each read the stream independently.

One Kafka topic per telemetry category, named to match the MQTT category
segment (see simulator's mqtt_topic()): iocl.atg, iocl.atg_alarm,
iocl.du_alarm, iocl.psp, iocl.iot, iocl.aip

Usage:
    pip install -r ../../requirements.txt
    python bridge_mqtt_to_kafka.py --broker localhost --kafka localhost:9092
"""
from __future__ import annotations

import argparse


def topic_category(mqtt_topic: str) -> str | None:
    """iocl/{ro_id}/{category}/{sub_id} -> category. Pure + testable."""
    parts = mqtt_topic.split("/")
    if len(parts) < 3 or parts[0] != "iocl":
        return None
    return parts[2]


def kafka_topic_for(category: str) -> str:
    return f"iocl.{category}"


def run(mqtt_broker: str, mqtt_port: int, kafka_bootstrap: str) -> None:
    import paho.mqtt.client as mqtt
    from confluent_kafka import Producer

    producer = Producer({"bootstrap.servers": kafka_bootstrap})

    def on_connect(client, userdata, flags, reason_code, properties=None):
        print(f"[bridge] connected to MQTT (rc={reason_code}); subscribing to iocl/#")
        client.subscribe("iocl/#")

    def on_message(client, userdata, msg):
        category = topic_category(msg.topic)
        if category is None:
            print(f"[bridge] WARN unrecognised topic, dropping: {msg.topic}")
            return
        producer.produce(kafka_topic_for(category), key=msg.topic.encode(), value=msg.payload)
        producer.poll(0)  # trigger delivery callbacks without blocking

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_broker, mqtt_port, keepalive=60)

    try:
        client.loop_forever()
    finally:
        producer.flush(10)


def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO MQTT -> Kafka bridge")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--kafka", default="localhost:9092", help="Kafka bootstrap servers")
    args = parser.parse_args()
    run(args.broker, args.port, args.kafka)


if __name__ == "__main__":
    main()
