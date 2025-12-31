# Audit and Deployment Guide for the Hypex E-commerce API

## 1. Introduction

This document provides a practical guide for developers and DevOps engineers working on the Hypex E-commerce API. It summarizes key audit fixes, documents local development options, and outlines the production Docker Compose deployment path that matches this repository.

## 2. Security Audit Summary

An audit of the project was conducted to identify security vulnerabilities and areas for improvement. The following critical issues were identified and have been addressed:

-   **`DEBUG` Mode Disabled in Production**: The application is no longer configured to run with `DEBUG=True` in production environments.
-   **`ALLOWED_HOSTS` Secured**: The `ALLOWED_HOSTS` setting is no longer a wildcard and must be explicitly configured for each environment.
-   **Secure Cookie Configuration**: `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are now enabled by default for production.
-   **Non-Root Docker User**: The `Dockerfile` has been updated to run the application as a non-root user, significantly reducing the container's attack surface.
-   **Separation of Dependencies**: Development-specific dependencies have been moved to `requirements-dev.txt` to avoid installing them in the production image.
-   **`.gitignore` Added**: A `.gitignore` file has been added to prevent sensitive files like `.env` and build artifacts from being committed.

## 3. Local Development Setup

You can develop either directly on your machine (recommended for faster feedback) or with Docker Compose (production-like).

### Option A: Local Python Environment

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/amirhossein-moloki/django-ecommerce-api.git
    cd django-ecommerce-api
    ```

2.  **Create and Configure Environment File**
    ```bash
    cp .env.example .env
    ```
    Update `.env` with development values, especially `DEBUG=True`, `DJANGO_SETTINGS_MODULE=ecommerce_api.settings.development`, and local SMTP settings.

3.  **Install Dependencies and Run**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    python manage.py migrate
    python manage.py runserver
    ```

### Option B: Docker Compose (Production-Like)

1.  **Create Environment File**
    ```bash
    cp .env.example .env
    ```

2.  **Build and Run the Services**
    ```bash
    docker compose up --build
    ```

The API will be available at `http://localhost` (or `https://<DOMAIN>` when Certbot is enabled).

## 4. Deployment Guide (Docker Compose)

### Prerequisites

-   Docker
-   Docker Compose
-   A domain name (only required if you enable SSL)

### Steps

1.  **Configure Environment Variables**
    Update `.env` with production values, at minimum:
    - `SECRET_KEY`
    - `DEBUG=False`
    - `ALLOWED_HOSTS`
    - `DOMAIN`
    - `CERTBOT_EMAIL`
    - `CERTBOT_ENABLED=true` (only when using a real domain)

2.  **Start the Stack**
    ```bash
    docker compose up --build -d
    ```

3.  **Verify Health**
    ```bash
    docker compose ps
    docker compose logs -f nginx
    ```

## 5. CI/CD Notes

This repository does not include CI/CD workflows by default. If you need automated builds/deployments, add GitHub Actions (or your platform of choice) that:
- runs linting and tests (`pytest`),
- builds the Docker images, and
- deploys to your target environment.

## 6. Post-Deployment Checklist

-   [ ] **Verify containers**: `docker compose ps` shows all services healthy.
-   [ ] **Check logs**: `docker compose logs -f web` for application errors.
-   [ ] **Test endpoints**: verify core API endpoints and admin login.
-   [ ] **Background tasks**: confirm `celery_worker` and `celery_beat` are running.

## 7. Certificate Renewal

When `CERTBOT_ENABLED=true`, the Nginx container installs a cron job to renew certificates nightly and reload Nginx on success. You can confirm renewal activity in the Nginx container logs.
