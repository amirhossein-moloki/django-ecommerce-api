# ---- Build Stage ----
FROM python:3.13.3-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python-dev-is-python3 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /code

# Install dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY requirements.txt .
RUN uv pip install --upgrade pip -r requirements.txt --system


# ---- Final Stage ----
FROM python:3.13.3-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /code

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copy the Django project
COPY . .

# Expose the application port
EXPOSE 8000
