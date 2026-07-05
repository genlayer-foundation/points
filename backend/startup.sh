#!/bin/bash
set -e

echo "Starting Django application startup..."

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

case "${RUN_MIGRATIONS_ON_STARTUP:-true}" in
  false|False|FALSE|0|no|No|NO)
    echo "Skipping database migrations."
    ;;
  *)
    echo "Running database migrations with advisory lock..."
    python3 manage.py migrate_with_lock --noinput
    ;;
esac

echo "Startup complete. Starting Django server..."
exec "$@"
