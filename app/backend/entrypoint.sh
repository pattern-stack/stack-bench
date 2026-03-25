#!/bin/sh
set -e

echo "Running database migrations..."
uv run alembic upgrade head || echo "WARNING: migrations failed, starting server anyway"

echo "Starting server..."
exec uv run uvicorn organisms.api.app:app --host 0.0.0.0 --port 8000
