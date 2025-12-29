#!/bin/bash
set -e

echo "Waiting for PostgreSQL to start..."
# This is a simple loop to wait for the database.
# In a real production scenario, a more robust solution like wait-for-it.sh is recommended.
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "PostgreSQL started"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Daphne for ASGI (Channels)
echo "Starting Daphne server..."
daphne -b 0.0.0.0 -p 8001 ecommerce_api.asgi:application &

# Start Gunicorn for WSGI (main Django app)
echo "Starting Gunicorn server..."
/opt/venv/bin/gunicorn ecommerce_api.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --log-level "info"
