"""Analytics business logic: record events, compute aggregate stats."""
import logging

from .config import settings
from .repositories import AnalyticsRepository

log = logging.getLogger("analytics-service.service")


class AnalyticsService:
    def __init__(self) -> None:
        self._repo = AnalyticsRepository()

    def record_event(self, event_type: str, booking_id: int, slot_id: int, user_id: int) -> None:
        self._repo.insert_event(event_type, booking_id, slot_id, user_id)

    def get_stats(self) -> dict:
        created = self._repo.count_by_type(settings.kafka_topic_booking_created)
        cancelled = self._repo.count_by_type(settings.kafka_topic_booking_cancelled)
        return {
            "bookings_created": created,
            "bookings_cancelled": cancelled,
            "active_bookings": max(created - cancelled, 0),
            "unique_users": self._repo.unique_users(),
            "top_users": [
                {"user_id": uid, "bookings": n} for uid, n in self._repo.top_users()
            ],
        }
