#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Create a .env file from the example if it doesn't exist.
# This ensures that Docker Compose can find the necessary environment file
# before it attempts to start the services.
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Build and start the Docker containers in detached mode.
# Using 'sudo' to avoid permission issues with the Docker daemon.
echo "Starting Docker services..."
sudo docker compose up -d --build

echo "Setup complete. Services are running in the background."
