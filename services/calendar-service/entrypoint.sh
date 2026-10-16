#!/bin/sh
# Apply pending DB migrations, then start the API (which also launches the
# Kafka consumer thread). Running migrations at container start keeps every
# schema change explicit, versioned and reviewable — production practice.
set -e
echo "[entrypoint] applying database migrations..."
alembic upgrade head
echo "[entrypoint] starting calendar-service..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8003
