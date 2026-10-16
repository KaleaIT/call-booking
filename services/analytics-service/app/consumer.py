"""Kafka consumer: writes every booking event into ClickHouse."""
import json
import logging
import time

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from .config import settings
from .services import AnalyticsService

log = logging.getLogger("analytics-service.consumer")


def _build_consumer() -> KafkaConsumer:
    while True:
        try:
            return KafkaConsumer(
                settings.kafka_topic_booking_created,
                settings.kafka_topic_booking_cancelled,
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                group_id=settings.kafka_group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
        except NoBrokersAvailable:
            log.warning("Kafka not ready, retrying in 3s...")
            time.sleep(3)


def run_consumer() -> None:
    consumer = _build_consumer()
    service = AnalyticsService()
    log.info("analytics-service consumer started")
    for message in consumer:
        payload = message.value
        try:
            service.record_event(
                event_type=payload.get("event", message.topic),
                booking_id=int(payload["booking_id"]),
                slot_id=int(payload.get("slot_id", 0)),
                user_id=int(payload.get("user_id", 0)),
            )
            log.info("recorded %s for booking %s", message.topic, payload.get("booking_id"))
        except Exception:  # pragma: no cover - keep consumer alive
            log.exception("failed to record event")
