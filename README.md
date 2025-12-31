# Hypex eCommerce API (Dockerized)

<div align="center">
  <img src="https://raw.githubusercontent.com/amirhossein-moloki/django-ecommerce-api/main/docs/images/logo.png" alt="Hypex Logo" width="150"/>
  <p><strong>A production-ready, Dockerized deployment for the Hypex eCommerce API.</strong></p>
</div>

This project provides a complete, multi-container Docker setup for deploying the Hypex eCommerce API. It is designed for production use and includes a full suite of services orchestrated by Docker Compose, featuring automated SSL certificate acquisition and renewal with Nginx and Certbot.

## ✨ Key Features of this Deployment

- **🚀 Fully Containerized:** All services (Django, Nginx, PostgreSQL, Redis, Celery) run in isolated Docker containers.
- **🔒 Automated SSL:** Nginx can automatically obtain and renew SSL certificates from Let's Encrypt using Certbot when `CERTBOT_ENABLED=true` and `DOMAIN`/`CERTBOT_EMAIL` are set.
- **⚡ High Performance:** Nginx serves static and media files directly, while Gunicorn and Daphne run the Django application, providing a high-performance, scalable setup.
- **🔄 Idempotent Startup:** The startup scripts are designed to be idempotent. You can run them multiple times without causing issues. The system will configure itself correctly whether it's the first run or a restart.
- **📈 Production-Ready:** Includes Celery workers and a beat scheduler for background tasks, health checks for services, and a secure-by-default Nginx configuration.

## 🏗️ Architecture Overview

This setup consists of the following services:

- **`nginx`**: The reverse proxy that handles all incoming HTTP and HTTPS traffic. It is responsible for SSL termination (when Certbot is enabled), serving static/media files, and routing requests to the Django application.
- **`web`**: The Django application service, running both Gunicorn (for WSGI) and Daphne (for ASGI/Channels) servers.
- **`db`**: The PostgreSQL database for data persistence.
- **`redis`**: The Redis server, used for caching and as a message broker for Celery.
- **`celery_worker`**: A Celery worker process for executing asynchronous background tasks.
- **`celery_beat`**: The Celery beat scheduler for running periodic tasks.

##  Prerequisites

Before you begin, ensure you have the following installed on your server:

- **Docker:** [Get Docker](https://docs.docker.com/get-docker/)
- **Docker Compose:** [Install Docker Compose](https://docs.docker.com/compose/install/)
- A registered **domain name** that points to your server's public IP address.

## 🚀 Getting Started: First-Time Setup

Follow these steps to configure and launch the application for the first time.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/django-ecommerce-api.git
cd django-ecommerce-api
```

### 2. Configure Environment Variables

The entire stack is configured using an `.env` file. Create one by copying the example file:

```bash
cp .env.example .env
```

Now, open the `.env` file with a text editor and **update the following critical variables**:

- **`SECRET_KEY`**: Generate a new, strong secret key. You can use an online generator or a command-line tool.
- **`DEBUG`**: Set this to `False` for production.
- **`ALLOWED_HOSTS`**: Set this to your domain name (e.g., `api.yourdomain.com`).
- **`DOMAIN`**: **This is crucial when SSL is enabled.** Set this to your fully qualified domain name (e.g., `api.yourdomain.com`).
- **`CERTBOT_EMAIL`**: Set this to your email address. Let's Encrypt will use this to send you important notifications about your certificate.
- **`CERTBOT_ENABLED`**: Set to `true` to enable automatic certificate provisioning/renewal. For local development, keep this `false`.
- **Database and Redis settings**: The default values are fine for Docker Compose, as the services will be linked.

Example `.env` configuration:
```env
# ... other settings
SECRET_KEY=your-super-strong-secret-key
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com

DOMAIN=api.yourdomain.com
CERTBOT_EMAIL=your-email@yourdomain.com
CERTBOT_ENABLED=true
# ... other settings
```

### 3. Build and Launch the Stack

With the `.env` file configured, you can now build the images and start all the services.

```bash
sudo docker compose up --build -d
```

**What happens on the first run?**

- Docker Compose will build the custom Docker images for the `web` and `nginx` services.
- The `nginx` container's entrypoint script will detect that no SSL certificate exists.
- It will temporarily start Nginx on port 80 to serve the Let's Encrypt challenge.
- Certbot will be invoked to request a new SSL certificate for your domain.
- Once the certificate is successfully obtained, Nginx will be reloaded with the final HTTPS configuration.
- The Django container will run database migrations and collect static files before starting the application servers.

You can monitor the logs to see the progress, especially for the initial certificate acquisition:

```bash
sudo docker compose logs -f nginx
```

Once the process is complete, you should be able to access your API at `https://yourdomain.com`. For local development, set `CERTBOT_ENABLED=false` and use `http://localhost` instead.

## 🔄 Day-to-Day Management

### Starting and Stopping the Application

- **To start all services:**
  ```bash
  sudo docker compose up -d
  ```
- **To stop all services:**
  ```bash
  sudo docker compose down
  ```

### Viewing Logs

You can view the logs for any service by name:

```bash
# View logs for the Django application
sudo docker compose logs -f web

# View logs for Nginx
sudo docker compose logs -f nginx
```

### Running Management Commands

To run Django `manage.py` commands, you can use `docker compose exec`:

```bash
# Create a superuser
sudo docker compose exec web python manage.py createsuperuser

# Open a Django shell
sudo docker compose exec web python manage.py shell
```

## 🔐 SSL Certificate Renewal

When `CERTBOT_ENABLED=true`, the `nginx` container includes a cron job that runs daily to automatically renew your SSL certificate. No manual intervention is required. You can verify that the renewal process is working by checking the cron logs within the Nginx container.

##  volume Management

This setup uses named volumes to persist data. These volumes are managed by Docker.

- **`postgres_data`**: Stores the PostgreSQL database files.
- **`static_files`**: Stores the collected static files for Django.
- **`media_files`**: Stores user-uploaded media files.
- **`certbot_certs`**: Stores the SSL certificates from Let's Encrypt.
- **`certbot_webroot`**: Used by Certbot for the webroot challenge.

To inspect the volumes, you can use `docker volume ls`.

## Troubleshooting

- **"Port is already allocated" error:** This usually means another process on your host machine is using port 80 or 443. Stop the conflicting process before starting the stack.
- **Certbot fails:**
  - Ensure your domain's DNS A record is pointing correctly to your server's IP address.
  - Make sure ports 80 and 443 are open on your server's firewall.
  - Check the Certbot logs for specific error messages: `sudo docker compose logs nginx`.
- **502 Bad Gateway:** This typically means the `web` container is not running or is unhealthy. Check its logs for errors: `sudo docker compose logs web`.
