"""Kafka consumer that turns booking events into real-time notifications.

For every booking.created / booking.cancelled event we build TWO notifications
— one for the guest (who booked) and one for the host (slot owner) — and:
  * PUBLISH each to a Redis pub/sub channel (the ws-server is subscribed and
    pushes it to that user's WebSocket connections);
  * store it in a short per-user history list in Redis so the UI can show the
    last few notifications after a page reload.

There is no Celery anymore: delivery is near-real-time through Redis pub/sub.
"""
import json
import logging
import time
import uuid
from datetime import datetime, timezone

import redis
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from .config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("notification-service.consumer")


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


def _texts(kind: str) -> tuple[str, str]:
    """(текст для гостя, текст для хозяина) по типу события."""
    if kind == settings.kafka_topic_booking_created:
        return "Вы забронировали слот", "Ваш слот забронировали"
    return "Вы отменили бронь", "Бронь вашего слота отменена"


def _deliver(r: redis.Redis, recipient_id: int, notification: dict) -> None:
    """Опубликовать уведомление в pub/sub и сохранить в историю получателя."""
    payload = json.dumps(notification, default=str)
    r.publish(settings.notifications_channel, payload)
    key = settings.history_key(recipient_id)
    r.lpush(key, payload)
    r.ltrim(key, 0, settings.history_size - 1)


def _handle(r: redis.Redis, kind: str, event: dict) -> None:
    guest_id = event.get("user_id")
    owner_id = event.get("owner_id")
    guest_text, owner_text = _texts(kind)

    base = {
        "kind": "booking.created"
        if kind == settings.kafka_topic_booking_created
        else "booking.cancelled",
        "booking_id": event.get("booking_id"),
        "start_time": event.get("start_time"),
        "end_time": event.get("end_time"),
        "ts": datetime.now(timezone.utc).isoformat(),
    }

    recipients = [(guest_id, "guest", guest_text), (owner_id, "owner", owner_text)]
    for recipient_id, role, text in recipients:
        if recipient_id is None:
            continue
        notification = {
            **base,
            "id": uuid.uuid4().hex,
            "user_id": recipient_id,
            "role": role,
            "text": text,
        }
        _deliver(r, recipient_id, notification)


def main() -> None:
    r = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_notifications_db,
    )
    consumer = _build_consumer()
    log.info("notification-service consumer started")
    for message in consumer:
        try:
            _handle(r, message.topic, message.value)
            log.info("delivered notifications for %s", message.topic)
        except Exception:  # pragma: no cover - keep consumer alive
            log.exception("failed to deliver notification")


if __name__ == "__main__":
    main()
