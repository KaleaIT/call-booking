"""Data-access layer for ClickHouse. Only place that runs CH queries."""
from .clickhouse_client import get_client
from .config import settings


class AnalyticsRepository:
    def __init__(self) -> None:
        self._client = get_client()
        self._table = f"{settings.clickhouse_db}.booking_events"

    def insert_event(self, event_type: str, booking_id: int, slot_id: int, user_id: int) -> None:
        self._client.insert(
            self._table,
            [[event_type, booking_id, slot_id, user_id]],
            column_names=["event_type", "booking_id", "slot_id", "user_id"],
        )

    def count_by_type(self, event_type: str) -> int:
        rows = self._client.query(
            f"SELECT count() FROM {self._table} WHERE event_type = %(t)s",
            parameters={"t": event_type},
        ).result_rows
        return rows[0][0] if rows else 0

    def unique_users(self) -> int:
        rows = self._client.query(f"SELECT uniqExact(user_id) FROM {self._table}").result_rows
        return rows[0][0] if rows else 0

    def top_users(self, limit: int = 5) -> list[tuple[int, int]]:
        rows = self._client.query(
            f"""
            SELECT user_id, count() AS bookings
            FROM {self._table}
            WHERE event_type = 'booking.created'
            GROUP BY user_id
            ORDER BY bookings DESC
            LIMIT %(limit)s
            """,
            parameters={"limit": limit},
        ).result_rows
        return [(r[0], r[1]) for r in rows]
