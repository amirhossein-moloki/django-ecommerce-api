# Audit and Deployment Guide for the Hypex E-commerce API

## 1. Introduction

This document provides a comprehensive guide for developers and DevOps engineers involved in the Hypex E-commerce API project. It includes a summary of the initial security audit, instructions for setting up a local development environment, and a detailed walkthrough of the CI/CD pipeline for deploying the application to Kubernetes.

## 2. Security Audit Summary

An audit of the project was conducted to identify security vulnerabilities and areas for improvement. The following critical issues were identified and have been addressed:

-   **`DEBUG` Mode Disabled in Production**: The application is no longer configured to run with `DEBUG=True` in production environments.
-   **`ALLOWED_HOSTS` Secured**: The `ALLOWED_HOSTS` setting is no longer a wildcard and must be explicitly configured for each environment.
-   **Secure Cookie Configuration**: `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are now enabled by default for production.
-   **Non-Root Docker User**: The `Dockerfile` has been updated to run the application as a non-root user, significantly reducing the container's attack surface.
-   **Separation of Dependencies**: Development-specific dependencies have been moved to `requirements-dev.txt` to avoid installing them in the production image.
-   **`.gitignore` Added**: A `.gitignore` file has been added to prevent sensitive files like `.env` and build artifacts from being committed.

For a more detailed breakdown of the audit, please see the `CODE_REVIEW_REPORT.md` file.

## 3. Local Development Setup

The local development environment is managed by Docker Compose.

### Prerequisites

-   Docker
-   Docker Compose

### Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/m-h-s/E-commerce-api.git
    cd E-commerce-api
    ```

2.  **Create Environment File**
    Copy the example environment file.
    ```bash
    cp .env.example .env
    ```
    Update the `.env` file with your local configuration. For local development, the default values should work.

3.  **Build and Run the Services**
    Use the `docker-compose.dev.yml` file to build and run the development containers.
    ```bash
    docker-compose -f docker-compose.dev.yml up --build
    ```

    The application will be available at `http://localhost:8000`.

## 4. CI/CD Pipeline Overview

The project uses GitHub Actions for continuous integration and continuous deployment.

### CI Pipeline (`.github/workflows/ci.yml`)

The CI pipeline is triggered on every pull request to the `main` branch. It performs the following checks:

-   **Linting and Formatting**: Enforces code style with `ruff` and `black`.
-   **Security Analysis**: Scans for vulnerabilities with `bandit` and `pip-audit`.
-   **Testing**: Runs the `pytest` test suite.
-   **Docker Image Build & Scan**: Builds the production Docker image and scans it for OS vulnerabilities with `trivy`.
-   **Docker Image Build & Scan**: Builds the production Docker image and scans it for OS vulnerabilities with `trivy`.

### Staging Deployment Pipeline (`.github/workflows/cd.yml`)

This pipeline is triggered on every push to the `main` branch. Its purpose is to automatically deploy the latest version of the application to the staging environment.

-   **Build and Push Image**: Builds a new Docker image and pushes it to GHCR, tagged with the commit SHA.
-   **Deploy to Staging**: Deploys the newly built image to the `staging` namespace in Kubernetes.

### Production Deployment Pipeline (`.github/workflows/release.yml`)

This pipeline is triggered only when a new release is published on GitHub. This ensures that production deployments are intentional and tied to a specific version.

-   **Build and Push Image**: Builds a new Docker image and pushes it to GHCR, tagged with the release version (e.g., `v1.0.1`).
-   **Deploy to Production**: Deploys the newly built image to the `production` namespace in Kubernetes.

## 5. Deployment Guide

### Prerequisites

-   A Kubernetes cluster
-   `kubectl` configured to connect to your cluster
-   `helm` v3+

### Step 1: Configure GitHub Secrets

The CI/CD pipeline requires the following secrets to be set in your GitHub repository's settings (`Settings > Secrets and variables > Actions`):

-   `KUBECONFIG`: The contents of your `kubeconfig` file, which grants access to your Kubernetes cluster. This is a sensitive credential and should be handled with care.

### Step 2: Create Kubernetes Secrets

The application requires several secrets to be present in the Kubernetes cluster. You can create them using `kubectl`.

First, create a `secrets.yaml` file with your secret values:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: django-secrets
type: Opaque
stringData:
  SECRET_KEY: "your-super-secret-key"
  DATABASE_URL: "postgres://user:password@host:port/db"
  REDIS_URL: "redis://host:port/0"
  GOOGLE_OAUTH2_KEY: "your-google-oauth2-key"
  GOOGLE_OAUTH2_SECRET: "your-google-oauth2-secret"
```

Apply this to each namespace where you will deploy the application:
```bash
kubectl apply -f secrets.yaml --namespace staging
kubectl apply -f secrets.yaml --namespace production
```

### Step 3: Automated Deployment

-   **To Staging**: Push your changes to the `main` branch.
-   **To Production**: Create a new release on the GitHub repository.

### Step 4: Manual Deployment (Optional)

You can also deploy the application manually using Helm.

```bash
# For Staging
helm upgrade --install staging-ecommerce-api ./helm \
  --namespace staging \
  --create-namespace \
  --set image.repository=ghcr.io/your-repo/ecommerce-api \
  --set image.tag=your-image-tag \
  --set ingress.hosts[0].host=staging.your-domain.com

# For Production
helm upgrade --install prod-ecommerce-api ./helm \
  --namespace production \
  --create-namespace \
  --set image.repository=ghcr.io/your-repo/ecommerce-api \
  --set image.tag=your-image-tag \
  --set ingress.hosts[0].host=your-domain.com
```

## 6. Post-Deployment Checklist

-   [ ] **Verify Pods**: Check that all pods are running (`kubectl get pods -n <namespace>`).
-   [ ] **Check Logs**: Inspect the logs for any errors (`kubectl logs -f <pod-name> -n <namespace>`).
-   [ ] **Test Ingress**: Ensure the application is accessible via the configured domain.
-   [ ] **Run Smoke Tests**: Perform basic checks to confirm the core functionality is working.

## 7. Improving Health Probes

For more reliable health checks in Kubernetes, it is recommended to create a dedicated health check endpoint (e.g., `/healthz`) that does not perform any database queries. This ensures that the application is marked as healthy even if the database is temporarily unavailable, preventing cascading failures.

Once this endpoint is created, you can update the `helm/templates/deployment.yaml` file to use it for the liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /healthz  # Update this path
    port: http
readinessProbe:
  httpGet:
    path: /healthz  # Update this path
    port: http
```

## 8. TODO for Project Owner

-   [ ] Update the `helm/values.yaml` and `.github/workflows/cd.yml` files with your actual domain names.
-   [ ] Set the `KUBECONFIG` secret in your GitHub repository.
-   [ ] Create the `django-secrets` secret in your Kubernetes cluster with your production credentials.
-   [ ] Configure your DNS to point your domain to the Ingress controller's external IP address.
