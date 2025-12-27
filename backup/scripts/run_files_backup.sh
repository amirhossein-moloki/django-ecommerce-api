#!/bin/bash
set -e
set -o pipefail

# ==============================================================================
# run_files_backup.sh
#
# Description:
#   This script automates the backup of media files and other assets using
#   Restic. It performs an incremental backup, applies a retention policy,
#   and can be scheduled via cron.
#
# Requirements:
#   - restic: Must be installed and available in the system's PATH.
#   - Environment variables for secrets must be set.
#
# Author:
#   Jules, Senior SRE
# ==============================================================================

# --- Configuration ---
# The directory containing the media files to be backed up.
BACKUP_SOURCE_DIR="${BACKUP_SOURCE_DIR:-/var/www/media}"

# --- Environment Variable Checks ---
# Ensure all necessary environment variables for Restic are set.
# These should be configured in the cronjob environment or a secrets manager.

if [[ -z "$RESTIC_REPOSITORY" ]]; then
  echo "Error: RESTIC_REPOSITORY environment variable is not set." >&2
  echo "Example: export RESTIC_REPOSITORY=s3:s3.your-region.amazonaws.com/your-bucket/media" >&2
  exit 1
fi

if [[ -z "$RESTIC_PASSWORD" ]]; then
  echo "Error: RESTIC_PASSWORD environment variable is not set." >&2
  echo "This is the encryption password for the Restic repository." >&2
  exit 1
fi

if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" ]]; then
  echo "Error: AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY are not set." >&2
  exit 1
fi

# --- Main Logic ---

echo "Starting Restic file backup process for ${BACKUP_SOURCE_DIR}..."

# Check if the repository is already initialized. If not, initialize it.
# The `list keys` command will fail if the repo doesn't exist,
# allowing us to run the `init` command.
if ! restic list keys &>/dev/null; then
  echo "Restic repository not found. Initializing a new one..."
  restic init
  echo "✅ New Restic repository initialized at ${RESTIC_REPOSITORY}."
else
  echo "Restic repository found. Proceeding with backup."
fi

# --- Perform Backup ---
echo "Running backup..."
# Create a new backup snapshot. Restic handles incrementals automatically.
# --verbose=1 shows which files are being processed.
restic backup "$BACKUP_SOURCE_DIR" --verbose=1

# --- Apply Retention Policy ---
echo "Applying retention policy..."
# The 'forget' command prunes old snapshots according to the specified policy.
# This keeps the repository size manageable.
# --prune option removes the actual data that is no longer needed.
restic forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 12 \
  --keep-yearly 3 \
  --prune

echo "------------------------------------------------------------------"
echo "✅ Restic file backup and retention policy application completed."
echo "------------------------------------------------------------------"
