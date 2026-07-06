#!/bin/bash
set -e

echo "Starting Django application startup..."

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# production should later run migrations once during deploy, then set RUN_MIGRATIONS_ON_STARTUP=false.
if [ "${RUN_MIGRATIONS_ON_STARTUP:-true}" = "false" ]; then
  echo "Skipping database migrations."
else
  echo "Running database migrations with advisory lock..."
  python3 manage.py migrate_with_lock --noinput
fi

echo "Startup complete. Starting Django server..."
exec "$@"
