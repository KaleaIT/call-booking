#!/bin/sh
# Apply pending DB migrations, then start the API. Running migrations at
# container start (rather than create_all in app code) keeps every schema
# change explicit, versioned and reviewable — production practice.
set -e
echo "[entrypoint] applying database migrations..."
alembic upgrade head
echo "[entrypoint] starting auth-service..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
