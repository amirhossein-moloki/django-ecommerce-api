# Hypex eCommerce API (Django REST Framework)

Hypex is a production-oriented eCommerce backend API built with Django and Django REST Framework (DRF).
It includes JWT authentication, Redis caching, Celery background tasks, OpenAPI/Swagger documentation, and core commerce modules like products, cart, orders, payments, coupons, shipping, plus real-time chat via Django Channels.

Keywords: Django eCommerce API, DRF eCommerce, REST API, JWT, Redis, Celery, Docker, Swagger, OpenAPI, Orders, Payments, Coupons, Shipping

---

## ✨ Highlights (What you get out of the box)

- Modular, scalable architecture (clean separation of domains)
- Auth & Accounts: JWT auth (djoser, simplejwt), profiles, addresses, OTP/SMS
- Catalog: products, categories, reviews, tagging, advanced search
- Cart & Checkout: persistent cart, order lifecycle, coupons/discounts
- Payments & Shipping: payment module + shipping options/costs
- Async & Performance: Celery + Redis for background jobs and Redis caching
- Docs: OpenAPI 3 schema with Swagger UI / ReDoc via drf-spectacular
- Real-time: chat support using Django Channels (ASGI)
- DevOps ready: Docker + Docker Compose, Nginx config, Helm chart included
- Observability: Prometheus metrics + OpenTelemetry tracing hooks

---

## 🧩 Tech Stack

- Backend: Django, Django REST Framework (DRF)
- Auth: JWT (djoser, simplejwt), Google social login
- Cache / Queue: Redis, Celery
- Docs: drf-spectacular (OpenAPI 3, Swagger UI, ReDoc)
- Realtime: Django Channels
- Deployment: Docker, Docker Compose, Nginx, Helm (Kubernetes)

---

## 🚀 Quickstart (Docker)

Prerequisites:
- Docker
- Docker Compose

Run locally:
```bash
git clone https://github.com/amirhossein-moloki/django-ecommerce-api.git
cd django-ecommerce-api
cp .env.example .env
docker-compose up -d --build
```

---

## 🔗 API Endpoints

- API Root: `http://localhost:80/api/v1/`
- Swagger UI: `http://localhost:80/api/v1/schema/swagger-ui/`
- ReDoc: `http://localhost:80/api/v1/schema/redoc/`
- Admin Panel: `http://localhost:80/admin/`
- Celery Monitoring (Flower): `http://localhost:5555/`

---

## ✅ Tests & Coverage

Run tests:
```bash
docker-compose exec web pytest
```

Coverage:
```bash
docker-compose exec web coverage run -m pytest
docker-compose exec web coverage report
```

---

## 🛠️ Debugging

View logs:
```bash
docker-compose logs -f <service_name>
```

Open a shell inside a container:
```bash
docker-compose exec web sh
```

Use Django shell_plus:
```bash
docker-compose exec web python manage.py shell_plus
```

---

## 🏗️ Architecture & Design Docs

- High-Level Architecture: `./docs/ARCHITECTURE.md`
- Database ERD: `./docs/DATABASE.md`
- Order Creation Sequence: `./docs/ORDER_SEQUENCE.md`

---

## 🧱 Project Structure

```text
.
├── account/        # JWT auth, profiles, addresses, OTP/SMS
├── cart/           # persistent cart logic
├── chat/           # real-time support chat (Channels)
├── coupons/        # discounts & promo codes
├── docs/           # architecture + ERD + workflows
├── ecommerce_api/  # settings, urls, ASGI/WSGI
├── helm/           # kubernetes helm chart
├── nginx/          # nginx configs
├── orders/         # order lifecycle, history, status
├── payment/        # payment gateways/integrations
├── shipping/       # shipping methods & pricing
├── shop/           # products, categories, reviews, search, tags
├── sms/            # notifications, OTP
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── manage.py
```

---

## 🧯 Production Notes (Checklist)

Before going live:
- Set `DEBUG=False` and configure `ALLOWED_HOSTS`
- Use proper secrets management (Kubernetes Secrets / Vault / Docker Secrets)
- Enforce HTTPS behind Nginx / Load Balancer
- Use managed PostgreSQL + managed Redis for reliability
- Offload static/media to object storage (e.g., S3) + CDN
- Add CI/CD (lint, tests, build image, deploy)
- Centralize logs + enable APM/tracing (OpenTelemetry)
- Configure health checks and autoscaling
