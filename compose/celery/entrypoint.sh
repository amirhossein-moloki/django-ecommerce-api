#!/bin/bash
set -e

# Wait for PostgreSQL to become available.
echo "Waiting for PostgreSQL to start..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "PostgreSQL started"

# Execute the command passed to the container (e.g., celery worker or beat).
exec "$@"
