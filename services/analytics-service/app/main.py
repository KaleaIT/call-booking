import logging
import threading

from fastapi import FastAPI

from .clickhouse_client import init_schema
from .consumer import run_consumer
from .services import AnalyticsService

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("analytics-service")

app = FastAPI(
    title="analytics-service",
    version="1.0.0",
    docs_url="/analytics/docs",
    redoc_url="/analytics/redoc",
    openapi_url="/analytics/openapi.json",
)


@app.on_event("startup")
def on_startup() -> None:
    init_schema()
    thread = threading.Thread(target=run_consumer, daemon=True, name="kafka-consumer")
    thread.start()
    log.info("analytics-service started, consumer thread launched")


@app.get("/health")
@app.get("/analytics/health")
def health() -> dict:
    return {"status": "ok", "service": "analytics-service"}


@app.get("/analytics/stats")
def stats() -> dict:
    """Aggregate booking statistics from ClickHouse."""
    return AnalyticsService().get_stats()
