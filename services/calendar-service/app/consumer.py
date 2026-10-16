"""Kafka consumer: only reads Kafka and delegates to CalendarService.

booking.created   -> create a Google Calendar event per connected participant
booking.updated   -> re-sync event details (description / meeting link)
booking.cancelled -> delete the events + mark the links cancelled
"""
import json
import logging
import time

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from .config import settings
from .database import SessionLocal
from .services import CalendarService

log = logging.getLogger("calendar-service.consumer")


def _build_consumer() -> KafkaConsumer:
    # Kafka may still be coming up when this service starts; retry.
    while True:
        try:
            return KafkaConsumer(
                settings.kafka_topic_booking_created,
                settings.kafka_topic_booking_updated,
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


def _dispatch(topic: str, payload: dict) -> None:
    # Fresh session+service per message (the unit of work for this event).
    with SessionLocal() as db:
        service = CalendarService(db)
        if topic == settings.kafka_topic_booking_created:
            service.on_booking_created(
                payload["booking_id"],
                payload.get("owner_id"),
                payload.get("user_id"),
                payload.get("start_time"),
                payload.get("end_time"),
                payload.get("description"),
                payload.get("meeting_link"),
            )
        elif topic == settings.kafka_topic_booking_updated:
            service.on_booking_updated(
                payload["booking_id"],
                payload.get("owner_id"),
                payload.get("user_id"),
                payload.get("start_time"),
                payload.get("end_time"),
                payload.get("description"),
                payload.get("meeting_link"),
            )
        elif topic == settings.kafka_topic_booking_cancelled:
            service.on_booking_cancelled(payload["booking_id"])


def run_consumer() -> None:
    consumer = _build_consumer()
    log.info("calendar-service consumer started")
    for message in consumer:
        try:
            _dispatch(message.topic, message.value)
        except Exception:  # pragma: no cover - keep consumer alive
            log.exception("error handling message from %s", message.topic)
