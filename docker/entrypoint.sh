#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
uv run alembic upgrade head

# Start the application
echo "Starting Glee server..."
exec uv run python -m glee
