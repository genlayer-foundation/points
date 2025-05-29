#!/bin/bash
set -e

echo "Starting Django application startup..."

echo "Collecting static files..."
pipenv run python3 manage.py collectstatic --noinput

echo "Running database migrations..."
pipenv run python3 manage.py migrate --noinput

echo "Startup complete. Starting Django server..."
exec "$@"