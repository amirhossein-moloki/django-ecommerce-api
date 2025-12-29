#!/bin/bash
set -e

# Wait for PostgreSQL to become available.
echo "Waiting for PostgreSQL to start..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "PostgreSQL started"

# Wait for Celery broker (Redis) to become available.
if [ -n "${CELERY_BROKER_URL:-}" ]; then
  echo "Waiting for Celery broker to start..."
  broker_host_port=$(python - <<'PY' 2>/dev/null || true
import os
from urllib.parse import urlparse

url = os.environ.get("CELERY_BROKER_URL", "")
if not url:
    raise SystemExit(0)

parsed = urlparse(url)
if parsed.scheme not in {"redis", "rediss"}:
    raise SystemExit(0)

host = parsed.hostname or ""
port = parsed.port or 6379
if host:
    print(f"{host}:{port}")
PY
  )

  if [ -n "$broker_host_port" ]; then
    broker_host="${broker_host_port%:*}"
    broker_port="${broker_host_port#*:}"
    while ! nc -z "$broker_host" "$broker_port"; do
      sleep 1
    done
    echo "Celery broker started"
  fi
fi

# Execute the command passed to the container (e.g., celery worker or beat).
exec "$@"
