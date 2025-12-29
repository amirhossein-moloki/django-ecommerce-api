# Stage 1: Builder
# This stage installs dependencies into a virtual environment.
FROM python:3.11-slim-bullseye AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/venv

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv .
COPY requirements.txt .
RUN . /opt/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
# This stage creates the final production image for Celery.
FROM python:3.11-slim-bullseye AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"
ENV DJANGO_SETTINGS_MODULE=ecommerce_api.settings.production

# Create a non-root user for security
RUN useradd -m -s /bin/bash app_user

WORKDIR /app

# Install runtime OS dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 netcat-openbsd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY . .

# Copy the entrypoint script and make it executable
COPY ./compose/celery/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Change ownership of the app directory
RUN chown -R app_user:app_user /app

# Switch to the non-root user
USER app_user

ENTRYPOINT ["/entrypoint.sh"]
