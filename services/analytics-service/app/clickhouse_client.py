"""ClickHouse connection + schema bootstrap.

Stores one row per booking event. Stats are computed with aggregate queries.
"""
import logging
import time

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from .config import settings

log = logging.getLogger("analytics-service.clickhouse")
_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
        )
    return _client


def init_schema() -> None:
    # Retry: ClickHouse may still be starting.
    for attempt in range(30):
        try:
            client = get_client()
            client.command(f"CREATE DATABASE IF NOT EXISTS {settings.clickhouse_db}")
            client.command(
                f"""
                CREATE TABLE IF NOT EXISTS {settings.clickhouse_db}.booking_events (
                    event_type  LowCardinality(String),
                    booking_id  UInt64,
                    slot_id     UInt64,
                    user_id     UInt64,
                    event_time  DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY (event_time, booking_id)
                """
            )
            log.info("ClickHouse schema ready")
            return
        except Exception as exc:  # pragma: no cover - infra warmup
            log.warning("ClickHouse not ready (%s), retrying... [%s/30]", exc, attempt + 1)
            time.sleep(3)
    raise RuntimeError("ClickHouse never became available")
