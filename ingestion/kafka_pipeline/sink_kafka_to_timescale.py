"""
Sentinel-RO — ingestion, path B, stage 2: Kafka -> TimescaleDB sink.

Consumes the topics bridge_mqtt_to_kafka.py produces and writes into the
same TimescaleDB schema as the direct path. Deliberately reuses the exact
row-shaping functions from direct_mqtt_to_timescale.py (imported, not
duplicated) — the parsing/validation logic is identical either way; only
the transport in front of it changes. That's the whole point of putting
Kafka in the middle: it's additive, not a rewrite.

Usage:
    pip install -r ../../requirements.txt
    export SENTINEL_DB_DSN="dbname=sentinel user=sentinel password=sentinel host=localhost"
    python sink_kafka_to_timescale.py --kafka localhost:9092
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Reuse the row-shaping functions from the direct-path script instead of
# duplicating them — see that file's docstring for why they're pure/testable.
from ingestion.direct_mqtt_to_timescale import TOPIC_HANDLERS  # noqa: E402

KAFKA_TOPICS = [f"iocl.{category}" for category in TOPIC_HANDLERS]


def category_from_kafka_topic(kafka_topic: str) -> str | None:
    if not kafka_topic.startswith("iocl."):
        return None
    return kafka_topic.split(".", 1)[1]


def run(kafka_bootstrap: str, dsn: str) -> None:
    import psycopg2
    from confluent_kafka import Consumer

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cursor = conn.cursor()

    consumer = Consumer({
        "bootstrap.servers": kafka_bootstrap,
        "group.id": "sentinel-ro-timescale-sink",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe(KAFKA_TOPICS)

    counts: dict[str, int] = {}
    print(f"[sink] subscribed to {KAFKA_TOPICS}")
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[sink] WARN kafka error: {msg.error()}")
                continue

            category = category_from_kafka_topic(msg.topic())
            if category is None or category not in TOPIC_HANDLERS:
                print(f"[sink] WARN unroutable topic, skipping: {msg.topic()}")
                continue

            shaper, sql = TOPIC_HANDLERS[category]
            try:
                row = shaper(json.loads(msg.value()))
                cursor.execute(sql, row)
                counts[category] = counts.get(category, 0) + 1
                if sum(counts.values()) % 50 == 0:
                    print(f"[sink] running totals: {counts}")
            except Exception as exc:  # noqa: BLE001 — log and keep consuming
                print(f"[sink] WARN dropped message on {msg.topic()}: {exc}")
    except KeyboardInterrupt:
        print("\n[sink] stopping.")
    finally:
        consumer.close()


def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO Kafka -> TimescaleDB sink")
    parser.add_argument("--kafka", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--dsn", default=os.environ.get("SENTINEL_DB_DSN",
                         "dbname=sentinel user=sentinel password=sentinel host=localhost"))
    args = parser.parse_args()
    run(args.kafka, args.dsn)


if __name__ == "__main__":
    main()
