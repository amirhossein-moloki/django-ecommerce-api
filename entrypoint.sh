#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Execute the command passed to this script.
# For example, if the Docker CMD is `gunicorn ...`, then `"$@"` will be `gunicorn ...`.
exec "$@"
