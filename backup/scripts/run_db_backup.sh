#!/bin/bash
set -e
set -o pipefail

# ==============================================================================
# run_db_backup.sh
#
# Description:
#   This script automates PostgreSQL backups using WAL-G. It supports
#   creating full base backups and is the entry point for the backup strategy.
#   It's designed to be called by a cronjob or a systemd timer.
#
# Requirements:
#   - wal-g: Must be installed and available in the system's PATH.
#   - Environment variables for secrets (see load_config function).
#
# Author:
#   Jules, Senior SRE
# ==============================================================================

# --- Configuration ---
# Path to the directory containing this script, used to find other files.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/walg_config.json"
PG_DATA_DIR="${PG_DATA_DIR:-/var/lib/postgresql/data}" # Use env var or default

# --- Functions ---

# Load configuration from the JSON file and export it for wal-g.
# This approach avoids hardcoding secrets in the script.
load_config() {
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: WAL-G config file not found at ${CONFIG_FILE}" >&2
    exit 1
  fi

  # Use jq to parse the JSON and export each key-value pair as an env var.
  # This makes the variables available to the wal-g process.
  export $(jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' "$CONFIG_FILE")

  # Also export standard PostgreSQL variables for wal-g to connect.
  # These should be set in the environment where the cronjob runs.
  export PGHOST="${PGHOST:-/var/run/postgresql}"
  export PGPORT="${PGPORT:-5432}"
  export PGUSER="${PGUSER:-postgres}"
  export PGDATABASE="${PGDATABASE:-postgres}"
  # PGPASSWORD should be set via ~/.pgpass or an environment variable.
}

# --- Main Logic ---

echo "Starting PostgreSQL backup process..."
load_config

echo "Configuration loaded. Taking a new full base backup..."

# This command creates a new full backup of the PostgreSQL data directory.
# WAL-G uploads it, compressed and encrypted, to the configured S3 bucket.
# This base backup is essential for Point-in-Time-Recovery (PITR).
wal-g backup-push "$PG_DATA_DIR"

echo "------------------------------------------------------------------"
echo "✅ Full base backup successfully completed."
echo ""
echo "Reminder for PITR setup:"
echo "To enable continuous archiving (Point-in-Time-Recovery), ensure your"
echo "postgresql.conf contains the following settings:"
echo ""
echo "  archive_mode = on"
echo "  archive_command = 'wal-g wal-push %p'"
echo "  archive_timeout = 60"
echo ""
echo "After setting this, reload your PostgreSQL configuration."
echo "------------------------------------------------------------------"
