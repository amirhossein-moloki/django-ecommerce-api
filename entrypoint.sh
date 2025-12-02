#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be ready.
# The `wait-for-it.sh` script is a utility that waits for a TCP host and port
# to be available before executing a command. Here, it waits for the PostgreSQL
# database service, which is named 'database' in docker-compose.yml, on port 5432.
# The `--timeout=0` means it will wait indefinitely.
# The `--` separates the options for `wait-for-it.sh` from the command to be executed.
./wait-for-it.sh database:5432 --timeout=0 -- echo "Database is ready."

# Apply database migrations.
# It's a good practice to run migrations on startup to ensure the database
# schema is up-to-date with the application's models.
python manage.py migrate

# Execute the command passed to this script.
# This allows the same entrypoint to be used for different services (web, celery, etc.)
# by passing different commands in the docker-compose file.
# For example, for the web server, `"$@"` will be `gunicorn ...`.
exec "$@"
