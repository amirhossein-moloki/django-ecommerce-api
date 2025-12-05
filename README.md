# Hypex E-commerce API

Welcome to the Hypex E-commerce API, a scalable and feature-rich backend solution built with Django and Django REST Framework.

## Core Features

-   **Modular Architecture**: Built with a clean, decoupled architecture using logical Django apps to ensure maintainability and scalability.
-   **Comprehensive E-commerce Platform**: Delivers a full suite of e-commerce functionalities, including product catalog management, a persistent shopping cart, streamlined order processing, secure payment integrations, and a flexible coupon system.
-   **Robust Authentication**: Implements secure, token-based authentication using JSON Web Tokens (JWT), managed by `djoser` and `simple_jwt` for enhanced security.
-   **Social Logins**: Supports social authentication with Google, allowing users to sign up and log in with a single click.
-   **Automated API Documentation**: Generates interactive and comprehensive API documentation with `drf-spectacular`, compatible with OpenAPI 3.
-   **Efficient Background Tasks**: Leverages `Celery` and `Redis` to manage asynchronous tasks, such as sending emails and processing notifications, without blocking the main application thread.
-   **High-Performance Caching**: Integrates `Redis` for caching frequently accessed data, significantly reducing response times and database load.
-   **Real-Time Capabilities**: Features a real-time chat system powered by Django Channels, enabling instant communication between users and support.
-   **Containerized Environment**: Fully containerized with Docker and Docker Compose, allowing for consistent and hassle-free development, testing, and deployment.
-   **Monitoring and Observability**: Includes built-in support for monitoring with Prometheus and tracing with OpenTelemetry, providing deep insights into application performance.

## Advanced Documentation

For a deeper understanding of the project's design and workflows, please refer to the following documents:

-   **[High-Level Architecture](./docs/ARCHITECTURE.md)**: A diagram and description of the system's architecture.
-   **[Database ERD](./docs/DATABASE.md)**: An Entity-Relationship Diagram of the core database models.
-   **[Order Creation Sequence](./docs/ORDER_SEQUENCE.md)**: A sequence diagram detailing the order creation process.

## Getting Started (Development)

This project is fully containerized to ensure a consistent and straightforward setup process. To get started, you will need Docker and Docker Compose installed on your system.

### Prerequisites

-   [Docker](https://docs.docker.com/get-docker/): The containerization platform.
-   [Docker Compose](https://docs.docker.com/compose/install/): A tool for defining and running multi-container Docker applications.

### Installation and Setup

1.  **Clone the Repository**:
    Begin by cloning the project repository to your local machine.
    ```bash
    git clone https://github.com/m-h-s/E-commerce-api.git
    cd E-commerce-api
    ```

2.  **Create the Environment File**:
    The project uses an environment file to manage configuration variables. Copy the example file to create your own local configuration.
    ```bash
    cp .env.example .env
    ```
    *Note: The default values in `.env.example` are pre-configured for the Docker setup and should work out of the box.*

3.  **Build and Launch with Docker Compose**:
    This command will build the Docker images, create the necessary containers, and start all the services in detached mode.
    ```bash
    docker-compose up -d --build
    ```

## Usage and Endpoints

Once the application is running, you can access the following endpoints:

-   **API Root**: `http://localhost:80/api/v1/`
-   **Interactive API Docs (Swagger UI)**: `http://localhost:80/api/v1/schema/swagger-ui/`
-   **Alternative API Docs (ReDoc)**: `http://localhost:80/api/v1/schema/redoc/`
-   **Admin Panel**: `http://localhost:80/admin/`
-   **Celery Monitoring (Flower)**: `http://localhost:5555/`

## Running Tests

To ensure the integrity and reliability of the codebase, a comprehensive test suite is included. You can run the tests using the following command:

```bash
docker-compose exec web pytest
```

To view a detailed test coverage report, you can use:
```bash
docker-compose exec web coverage run -m pytest
docker-compose exec web coverage report
```

## How to Debug

-   **View Logs**: Check the logs of a specific service.
    ```bash
    docker-compose logs -f <service_name>  # e.g., web, celery_worker
    ```
-   **Attach to a Running Container**: Access a shell inside a running container for interactive debugging.
    ```bash
    docker-compose exec <service_name> sh # e.g., web
    ```
-   **Use Django's `shell_plus`**: `shell_plus` (from `django-extensions`) is a powerful tool that auto-imports all your models.
    ```bash
    docker-compose exec web python manage.py shell_plus
    ```

## Production Deployment

Deploying this application to a production environment requires a more robust setup than the development configuration. The following guidelines outline key considerations for a secure, scalable, and reliable deployment.

### 1. **Security Best Practices**
-   **Environment Variables**: Never commit sensitive information, such as your `SECRET_KEY` or database credentials, directly to version control. Use a secure method for managing environment variables in your production environment, such as Docker Secrets, Kubernetes Secrets, or a dedicated secret management service like HashiCorp Vault.
-   **Disable Debug Mode**: Ensure that `DEBUG` is set to `False` in your production settings. This prevents sensitive information from being exposed in error pages.
-   **Configure `ALLOWED_HOSTS`**: Set `ALLOWED_HOSTS` to a list of your production domain names to prevent HTTP Host header attacks.
-   **HTTPS**: Enforce HTTPS across your entire application to encrypt data in transit. Use a reverse proxy like Nginx or a load balancer to terminate SSL/TLS.

### 2. **Scalability and Performance**
-   **Managed Database and Cache**: For production, it is highly recommended to use managed services for your database (e.g., AWS RDS for PostgreSQL) and cache (e.g., AWS ElastiCache for Redis). These services offer better performance, reliability, and scalability than self-hosted solutions.
-   **Static and Media Files**: Offload the serving of static and media files to a dedicated cloud storage service, such as Amazon S3. Use a Content Delivery Network (CDN), like Amazon CloudFront, to cache these assets and deliver them with low latency to users worldwide.
-   **Container Orchestration**: Use a container orchestration platform, such as Kubernetes or AWS ECS, to automate the deployment, scaling, and management of your application containers. A basic Helm chart is included in the `/helm` directory to help you get started with Kubernetes.
-   **Load Balancing**: Distribute incoming traffic across multiple instances of your application using a load balancer. This will improve availability and responsiveness.

### 3. **CI/CD Pipeline**
-   **Automated Workflow**: Implement a CI/CD pipeline to automate the testing, building, and deployment processes. This will ensure that every change is automatically verified before being deployed to production, reducing the risk of errors and improving release velocity.
-   **Pipeline Stages**: A typical CI/CD pipeline should include the following stages:
    1.  **Linting and Static Analysis**: Check for code quality and style issues.
    2.  **Unit and Integration Tests**: Run the automated test suite to validate the application's functionality.
    3.  **Build Docker Image**: Build and tag a new Docker image for the application.
    4.  **Push to Registry**: Push the Docker image to a container registry, such as Docker Hub, Amazon ECR, or Google Container Registry.
    5.  **Deploy to Production**: Automatically deploy the new image to your production environment.

### 4. **Monitoring and Logging**
-   **Centralized Logging**: Aggregate logs from all your application containers and services into a centralized logging platform (e.g., ELK Stack, Splunk, or Datadog). This will make it easier to search, analyze, and troubleshoot issues.
-   **Application Performance Monitoring (APM)**: Use an APM tool to monitor key performance metrics, such as response times, error rates, and transaction traces. The project is already instrumented with OpenTelemetry, which can be configured to send data to a compatible backend like Jaeger or Datadog.
-   **Health Checks**: Configure health check endpoints to allow your container orchestrator or load balancer to automatically detect and replace unhealthy instances of your application.

## Project Structure

The project follows a modular architecture where each Django app encapsulates a specific domain of functionality. This design promotes separation of concerns and enhances maintainability.

```
.
├── 📁 account/         # Manages user authentication, profiles, and address book.
├── 📁 cart/            # Handles shopping cart logic, including adding, updating, and clearing items.
├── 📁 chat/            # Implements real-time chat support for users.
├── 📁 coupons/         # Manages discount codes and promotional coupons.
├── 📁 docs/            # Contains supplementary documentation, including architecture diagrams and database schemas.
├── 📁 ecommerce_api/   # Core Django project with settings, root URL configuration, and ASGI/WSGI entrypoints.
│   └── 📁 settings/    # Splits settings into base, local, and production environments for better configuration management.
├── 📁 helm/            # Provides a Kubernetes Helm chart for streamlined deployment.
├── 📁 nginx/           # Includes Nginx configuration files for serving the application.
├── 📁 orders/          # Oversees order creation, processing, and history tracking.
├── 📁 payment/         # Integrates with payment gateways to handle transactions securely.
├── 📁 shipping/        # Manages shipping methods, costs, and logistics.
├── 📁 shop/            # Contains models and views for products, categories, and customer reviews.
├── 📁 sms/             # Handles SMS notifications and OTP verification.
├── 📄 .env.example    # Example environment file with configuration variables.
├── 📄 docker-compose.yml # Defines the services, networks, and volumes for the local development environment.
├── 📄 Dockerfile       # Specifies the build steps for the application's Docker image.
└── 📄 manage.py        # Django's command-line utility for administrative tasks.
```

### Key Applications

-   **`account`**: Manages user-related functionalities, including registration, authentication (JWT), profile management, and address storage.
-   **`shop`**: Powers the product catalog, handling categories, product details, reviews, and advanced search features.
-   **`cart`**: Implements a persistent shopping cart that works for both authenticated and anonymous users.
-   **`orders`**: Orchestrates the entire order lifecycle, from creation and validation to tracking and history.
-   **`payment`**: Provides a secure interface for processing payments through various gateways.
-   **`coupons`**: Allows for the creation and application of discount codes to orders.
-   **`shipping`**: Manages shipping options, calculates costs, and integrates with shipping providers.
-   **`chat`**: Enables real-time communication between customers and support agents.
-   **`sms`**: Handles sending SMS messages for notifications and one-time passwords (OTP).
