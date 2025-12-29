#!/bin/sh
set -e

# --- Helper Functions ---
log() {
  echo "[$(date -u)] [entrypoint.sh] $@"
}

# --- Environment Variable Checks ---
if [ -z "$DOMAIN" ]; then
  log "ERROR: The DOMAIN environment variable is not set."
  exit 1
fi

if [ -z "$EMAIL" ]; then
  log "ERROR: The EMAIL environment variable is not set (required by Let's Encrypt)."
  exit 1
fi

# --- Path Definitions ---
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
CERT_FILE="$CERT_DIR/fullchain.pem"
DHPARAMS_FILE="/etc/letsencrypt/ssl-dhparams.pem"
HTTP_CONF="/etc/nginx/conf.d/http.conf"
HTTPS_CONF="/etc/nginx/conf.d/https.conf"

# --- Main Logic ---

# Step 1: Check if a certificate already exists.
if [ -f "$CERT_FILE" ]; then
  log "Certificate found for $DOMAIN. Skipping acquisition."
else
  log "Certificate not found for $DOMAIN. Starting acquisition process..."

  # Temporarily disable the HTTPS config to start Nginx on port 80
  if [ -f "$HTTPS_CONF" ]; then
    log "Temporarily moving HTTPS config to allow Certbot challenge."
    mv "$HTTPS_CONF" "$HTTPS_CONF.disabled"
  fi

  # Start Nginx in the background to serve the challenge
  nginx -g "daemon on;"

  # Request the certificate
  log "Requesting Let's Encrypt certificate for $DOMAIN..."
  certbot certonly \
    --webroot -w /var/www/certbot \
    --email "$EMAIL" \
    --domain "$DOMAIN" \
    --rsa-key-size 4096 \
    --agree-tos \
    --non-interactive \
    --force-renewal

  # Stop the temporary Nginx instance
  log "Stopping temporary Nginx server."
  nginx -s stop
  # Wait for Nginx to fully stop
  while pgrep -x nginx > /dev/null; do sleep 1; done

  # Restore the HTTPS config
  if [ -f "$HTTPS_CONF.disabled" ]; then
    log "Restoring HTTPS config."
    mv "$HTTPS_CONF.disabled" "$HTTPS_CONF"
  fi
fi

# Step 2: Generate strong Diffie-Hellman parameters for enhanced security.
# This is done in the background if the file doesn't exist.
if [ ! -f "$DHPARAMS_FILE" ]; then
  log "Generating strong Diffie-Hellman parameters (4096 bits)..."
  log "This may take a few minutes."
  openssl dhparam -out "$DHPARAMS_FILE" 4096 &
fi

# Step 3: Setup a cron job for automatic certificate renewal.
log "Setting up cron job for automatic certificate renewal."
echo "0 3 * * * certbot renew --quiet && nginx -s reload" > /etc/crontabs/root
crond -b

# --- Final Execution ---
log "Substituting environment variables in Nginx config..."
envsubst '${DOMAIN}' < /etc/nginx/conf.d/http.conf.template > /etc/nginx/conf.d/http.conf
envsubst '${DOMAIN}' < /etc/nginx/conf.d/https.conf.template > /etc/nginx/conf.d/https.conf

log "Nginx is configured. Starting main process..."
# Execute the command passed to the script (e.g., `nginx -g 'daemon off;'`)
exec "$@"
