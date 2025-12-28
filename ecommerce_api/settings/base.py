import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
import django_cache_url
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Use python-dotenv to manage environment variables
load_dotenv(str(BASE_DIR / ".env"))
is_test_env = "test" in sys.argv or os.environ.get(
    "DJANGO_SETTINGS_MODULE", ""
).endswith(".test")
if is_test_env:
    load_dotenv(str(BASE_DIR / ".env.test"))


def get_env(name, default=None):
    """
    Helper function to get an environment variable. If the environment
    variable is not found and no default is specified, it raises an
    ImproperlyConfigured exception.
    """
    value = os.getenv(name, default)
    if value is None:
        raise ImproperlyConfigured(f"Set the {name} environment variable")
    return value


def get_env_bool(name, default=False):
    """
    Helper function to get a boolean value from environment variables.
    """
    value = os.getenv(name, str(default)).lower()
    return value in ("true", "1", "yes")


def get_env_list(name, default=""):
    """
    Helper function to get a list of strings from a comma-separated
    environment variable.
    """
    return [item.strip() for item in os.getenv(name, default).split(",") if item]


# -----------------------------------------------------------------------------
# C O R E   S E T T INGS
# -----------------------------------------------------------------------------
# These are critical settings that must be defined in the environment.
# The application will not start without them.

if is_test_env:
    SECRET_KEY = get_env("SECRET_KEY", "test-secret-key")
    DEBUG = get_env_bool("DEBUG", False)
else:
    DEBUG = get_env_bool("DEBUG", False)
    is_dev_env = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(".development")
    if DEBUG or is_dev_env:
        SECRET_KEY = get_env(
            "SECRET_KEY", "insecure-development-key-change-me"
        )
    else:
        SECRET_KEY = get_env("SECRET_KEY")

# Security settings
ALLOWED_HOSTS = get_env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = get_env_list("CSRF_TRUSTED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = get_env_bool("CORS_ALLOW_ALL_ORIGINS", False)
CORS_ALLOWED_ORIGINS = get_env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = get_env_bool("CORS_ALLOW_CREDENTIALS", True)

# Database and Cache
if is_test_env:
    DATABASES = {
        "default": dj_database_url.config(
            default="sqlite:///db.sqlite3", conn_max_age=600
        )
    }
    REDIS_URL = get_env("REDIS_URL", "locmemcache://")
else:
    DATABASES = {"default": dj_database_url.config(conn_max_age=600)}
    REDIS_URL = get_env("REDIS_URL")

CACHES = {"default": django_cache_url.parse(REDIS_URL)}


# Email
# NOTE: This implementation for email is basic. For production, you might
# need a more robust solution, potentially a separate library for parsing email URLs.
EMAIL_BACKEND = get_env(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = get_env("EMAIL_HOST", "")
EMAIL_PORT = int(get_env("EMAIL_PORT", 587))
EMAIL_USE_TLS = get_env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = get_env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = get_env("EMAIL_HOST_PASSWORD", "")

# Site settings
DOMAIN = get_env("DOMAIN", "localhost:8000")
SITE_NAME = get_env("SITE_NAME", "Hypex")
ADMINS = [tuple(s.split(":")) for s in get_env_list("ADMINS")]


# CORS settings
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_EXPOSE_HEADERS = ["csrftoken", "sessionid"]

# Application definition
#      ╭──────────────────────────────────────────────────────────╮
#      │                Application Configuration                 │
#      ╰──────────────────────────────────────────────────────────╯
# ───── Defines The Core, Third-party, And Custom Applications Used In The Project ─────

# Core Django applications provided by the framework
DJANGO_APPS = [
    "django.contrib.admin",  # Admin interface for managing the application
    "django.contrib.auth",  # Authentication framework
    "django.contrib.contenttypes",  # Content type system for permissions
    "django.contrib.sessions",  # Session framework
    "django.contrib.messages",  # Messaging framework
    "django.contrib.sites",  # Multi-site support
    "django.contrib.sitemaps",  # Sitemap generation
    "django.contrib.staticfiles",  # Static file management
    "django.contrib.postgres",  # PostgreSQL-specific features
]

# Third-party applications installed via pip
THIRD_PARTY_APPS = [
    "taggit",  # Tagging library for Django
    "drf_spectacular",  # OpenAPI schema generation for Django REST Framework
    "django_filters",  # Filtering support for Django REST Framework
    "rest_framework",  # Django REST Framework for building APIs
    "rest_framework.authtoken",  # Token-based authentication for REST Framework
    "django_redis",  # Redis cache backend
    "social_django",  # Social authentication (e.g., Google, Facebook)
    "djoser",  # User authentication and management
    "simple_history",  # Track changes to model instances
    "rest_framework_simplejwt.token_blacklist",  # JWT token blacklist for security
    "corsheaders",  # Cross-Origin Resource Sharing (CORS) headers
    "django_prometheus",  # Prometheus metrics for Django
    "django_ckeditor_5",  # CKEditor 5 for Django
]

# Custom applications developed for this project
CUSTOM_APPS = [
    "integrations",  # Integrations with third-party services like Torob and Emalls
    "common",  # Common utilities
    "shop",  # Shop application for managing products
    "cart",  # Cart application for managing shopping carts
    "orders",  # Orders application for managing customer orders
    "coupons",  # Coupons application for discounts
    "chat",  # Chat application for real-time communication
    "payment",  # Payment application for processing transactions
    "account",  # Account application for user management
    "shipping",
    "sms",
    "discounts.apps.DiscountsConfig",
    "blog",  # Blog application
]

# Combine all applications into the INSTALLED_APPS setting
INSTALLED_APPS = ["daphne"] + DJANGO_APPS + THIRD_PARTY_APPS + CUSTOM_APPS

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "cart.middleware.CartSessionMiddleware",  # Add custom cart session middleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "ecommerce_api.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ecommerce_api.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "account.UserAccount"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "EXCEPTION_HANDLER": "ecommerce_api.core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "ecommerce_api.utils.pagination.CustomPageNumberPagination",
    "DEFAULT_RENDERER_CLASSES": [
        "ecommerce_api.core.renderers.ApiResponseRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": get_env("DRF_ANON_THROTTLE_RATE", "400/day"),
        "user": get_env("DRF_USER_THROTTLE_RATE", "1000/day"),
    },
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

# JWT Authentication Tokens
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        days=int(get_env("JWT_ACCESS_TOKEN_LIFETIME_DAYS", 1))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(get_env("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7))
    ),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# API Documentation Settings
SPECTACULAR_SETTINGS = {
    "TITLE": get_env("API_DOCS_TITLE", "Hypex eCommerce API Documentation"),
    "DESCRIPTION": get_env(
        "API_DOCS_DESCRIPTION",
        "A scalable RESTful eCommerce API using Django, JWT auth, Redis caching, Celery for task scheduling, advanced search, tagging, and personalized results.",
    ),
    "VERSION": get_env("API_DOCS_VERSION", "1.2.6"),
    "SERVE_INCLUDE_SCHEMA": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "SORT_OPERATIONS": True,
    "SORT_SCHEMA_BY_TAGS": True,
    "ENUM_NAME_OVERRIDES": {},
    "COMPONENT_SPLIT_REQUEST": False,
    "ENABLE_DELETE_METHODS_WITH_BODY": True,
    "TAGS": [],
    "SECURITY": [{"bearerAuth": []}],
    "APPEND_PATH_TO_TAGS": False,
    "SCHEMA_EXTENSIONS": [],
}

# Django Debug Toolbar settings
INTERNAL_IPS = get_env_list("INTERNAL_IPS", "127.0.0.1,localhost")

# CKEditor 5 settings
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading",
            "|",
            "bold",
            "italic",
            "link",
            "bulletedList",
            "numberedList",
            "blockQuote",
            "imageUpload",
        ],
    }
}

CART_SESSION_ID = "cart"
SITE_ID = 1
ASGI_APPLICATION = "ecommerce_api.asgi.application"

# Channel layers for real-time features
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Logging configuration for development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
}

SMS_IR_OTP_TEMPLATE_ID = int(get_env("SMS_IR_OTP_TEMPLATE_ID", 123456))

POSTEX_SENDER_NAME = get_env("POSTEX_SENDER_NAME", "Your Company Name")
POSTEX_SENDER_PHONE = get_env("POSTEX_SENDER_PHONE", "Your Company Phone")
POSTEX_SENDER_ADDRESS = get_env("POSTEX_SENDER_ADDRESS", "Your Company Address")
POSTEX_SENDER_POSTAL_CODE = get_env(
    "POSTEX_SENDER_POSTAL_CODE", "Your Company Postal Code"
)
POSTEX_API_KEY = get_env("POSTEX_API_KEY", "")
POSTEX_FROM_CITY_CODE = int(get_env("POSTEX_FROM_CITY_CODE", 1))
POSTEX_SERVICE_TYPE = get_env("POSTEX_SERVICE_TYPE", "standard")

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "social_core.backends.google.GoogleOAuth2",
]

# Social Auth settings for Google OAuth2
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = get_env("GOOGLE_OAUTH2_KEY", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = get_env("GOOGLE_OAUTH2_SECRET", "")

DJOSER = {
    "HIDE_USERS": True,
    "EMAIL": {
        "activation": "account.emails.CustomActivationEmail",
    },
    "SERIALIZERS": {
        "user_create": "users.api.serializers.UserProfileSerializer",
        "user_delete": "djoser.serializers.UserDeleteSerializer",
    },
    "LOGIN_FIELD": "email",
    "SEND_ACTIVATION_EMAIL": True,
    "SEND_CONFIRMATION_EMAIL": True,
    "ACTIVATION_URL": "auth/activate/{uid}/{token}",
    "PASSWORD_RESET_CONFIRM_URL": "password/reset/confirm/{uid}/{token}",
    "USERNAME_RESET_CONFIRM_URL": "username/reset/confirm/{uid}/{token}",
    "PASSWORD_RESET_SHOW_EMAIL": True,
    "USERNAME_CHANGED_EMAIL_CONFIRMATION": True,
    "PASSWORD_CHANGED_EMAIL_CONFIRMATION": True,
    "USER_CREATE_PASSWORD_RETYPE": True,
}

LOGIN_URL = reverse_lazy("auth:jwt-create")
USERNAME_FIELD = "email"

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"',
        }
    },
    "USE_SESSION_AUTH": False,
}


TAGGIT_CASE_INSENSITIVE = True

# Zibal Payment Gateway
if is_test_env:
    ZIBAL_MERCHANT_ID = get_env("ZIBAL_MERCHANT_ID", "zibal")
    ZIBAL_WEBHOOK_SECRET = get_env(
        "ZIBAL_WEBHOOK_SECRET", "a-secret-for-zibal-webhooks"
    )
else:
    ZIBAL_MERCHANT_ID = get_env("ZIBAL_MERCHANT_ID")
    ZIBAL_WEBHOOK_SECRET = get_env("ZIBAL_WEBHOOK_SECRET")
ZIBAL_ALLOWED_IPS = get_env_list("ZIBAL_ALLOWED_IPS", "127.0.0.1")

# Celery Configuration
if is_test_env:
    CELERY_BROKER_URL = get_env("CELERY_BROKER_URL", "memory://")
    CELERY_RESULT_BACKEND = get_env(
        "CELERY_RESULT_BACKEND", "db+sqlite:///celery-results.sqlite"
    )
else:
    CELERY_BROKER_URL = get_env("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND = get_env("CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "cancel-pending-orders": {
        "task": "orders.tasks.cancel_pending_orders",
        "schedule": float(get_env("CANCEL_PENDING_ORDERS_INTERVAL", 600.0)),  # Default to 10 minutes
    },
}

# Session cookie settings
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = get_env_bool("SESSION_COOKIE_SECURE", True)
SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = True

# CSRF settings
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = get_env_bool("CSRF_COOKIE_SECURE", True)

# OpenTelemetry settings
OTEL_SERVICE_NAME = get_env("OTEL_SERVICE_NAME", "ecommerce-api")
OTEL_EXPORTER_OTLP_ENDPOINT = get_env(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318"
)

if OTEL_EXPORTER_OTLP_ENDPOINT:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource(attributes={"service.name": OTEL_SERVICE_NAME})

    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=f"{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces")
    )
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    DjangoInstrumentor().instrument()
