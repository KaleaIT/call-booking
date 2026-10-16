"""Kafka producer for booking lifecycle events.

The producer is created lazily and reused. Events are JSON-encoded. If Kafka
is briefly unavailable we log and continue — booking persistence is the
source of truth; downstream services are eventually consistent.
"""
import json
import logging

from kafka import KafkaProducer
from kafka.errors import KafkaError

from .config import settings

log = logging.getLogger("booking-service.events")
_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            retries=3,
        )
    return _producer


def _emit(topic: str, payload: dict) -> None:
    try:
        producer = _get_producer()
        producer.send(topic, payload)
        producer.flush(timeout=5)
        log.info("emitted %s: %s", topic, payload)
    except KafkaError as exc:  # pragma: no cover - infra failure path
        log.error("failed to emit %s: %s", topic, exc)


def emit_booking_created(
    booking_id: int,
    slot_id: int,
    user_id: int,
    owner_id: int,
    start_time,
    end_time,
    description=None,
    meeting_link=None,
) -> None:
    _emit(
        settings.kafka_topic_booking_created,
        {
            "event": "booking.created",
            "booking_id": booking_id,
            "slot_id": slot_id,
            "user_id": user_id,       # visitor / booker
            "owner_id": owner_id,     # host / slot owner
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "meeting_link": meeting_link,
        },
    )


def emit_booking_updated(
    booking_id: int,
    slot_id: int,
    user_id: int,
    owner_id: int,
    start_time,
    end_time,
    description=None,
    meeting_link=None,
) -> None:
    _emit(
        settings.kafka_topic_booking_updated,
        {
            "event": "booking.updated",
            "booking_id": booking_id,
            "slot_id": slot_id,
            "user_id": user_id,
            "owner_id": owner_id,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "meeting_link": meeting_link,
        },
    )


def emit_booking_cancelled(
    booking_id: int,
    slot_id: int,
    user_id: int,
    owner_id: int | None = None,
    start_time=None,
    end_time=None,
) -> None:
    # owner_id и времена нужны notification-service, чтобы уведомить обоих
    # участников (гостя и хозяина) об отмене с указанием времени слота.
    _emit(
        settings.kafka_topic_booking_cancelled,
        {
            "event": "booking.cancelled",
            "booking_id": booking_id,
            "slot_id": slot_id,
            "user_id": user_id,       # visitor / booker
            "owner_id": owner_id,     # host / slot owner
            "start_time": start_time,
            "end_time": end_time,
        },
    )
