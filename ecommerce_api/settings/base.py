import environ
from datetime import timedelta
from pathlib import Path

from django.urls import reverse_lazy

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Use django-environ to manage environment variables
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)
env.read_env(str(BASE_DIR / '.env'))

# -----------------------------------------------------------------------------
# C O R E   S E T T I N G S
# -----------------------------------------------------------------------------
# These are critical settings that must be defined in the environment.
# The application will not start without them.

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

# Security settings
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)

# Database and Cache
DATABASES = {'default': env.db('DATABASE_URL')}
CACHES = {'default': env.cache('REDIS_URL')}

# Email
EMAIL_CONFIG = env.email_url('EMAIL_URL', default='consolemail://')
vars().update(EMAIL_CONFIG)

# Site settings
DOMAIN = env('DOMAIN', default='localhost:8000')
SITE_NAME = env('SITE_NAME', default='Hypex')
ADMINS = [tuple(s.split(':')) for s in env.list('ADMINS', default=[])]


# CORS settings
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_EXPOSE_HEADERS = ['csrftoken', 'sessionid']

# Application definition
#      ╭──────────────────────────────────────────────────────────╮
#      │                Application Configuration                 │
#      ╰──────────────────────────────────────────────────────────╯
# ───── Defines The Core, Third-party, And Custom Applications Used In The Project ─────

# Core Django applications provided by the framework
DJANGO_APPS = [
    'django.contrib.admin',  # Admin interface for managing the application
    'django.contrib.auth',  # Authentication framework
    'django.contrib.contenttypes',  # Content type system for permissions
    'django.contrib.sessions',  # Session framework
    'django.contrib.messages',  # Messaging framework
    'django.contrib.sites',  # Multi-site support
    'django.contrib.sitemaps',  # Sitemap generation
    'django.contrib.staticfiles',  # Static file management
    'django.contrib.postgres',  # PostgreSQL-specific features
]

# Third-party applications installed via pip
THIRD_PARTY_APPS = [
    'taggit',  # Tagging library for Django
    'drf_spectacular',  # OpenAPI schema generation for Django REST Framework
    'debug_toolbar',  # Debugging tool for development
    'django_filters',  # Filtering support for Django REST Framework
    'rest_framework',  # Django REST Framework for building APIs
    'rest_framework.authtoken',  # Token-based authentication for REST Framework
    'django_redis',  # Redis cache backend
    'social_django',  # Social authentication (e.g., Google, Facebook)
    'djoser',  # User authentication and management
    'simple_history',  # Track changes to model instances
    'django_extensions',  # Additional management commands and utilities
    'rest_framework_simplejwt.token_blacklist',  # JWT token blacklist for security
    'corsheaders',  # Cross-Origin Resource Sharing (CORS) headers
    'django_prometheus',  # Prometheus metrics for Django
]

# Custom applications developed for this project
CUSTOM_APPS = [
    'shop.apps.ShopConfig',  # Shop application for managing products
    'cart.apps.CartConfig',  # Cart application for managing shopping carts
    'orders',  # Orders application for managing customer orders
    'coupons.apps.CouponsConfig',  # Coupons application for discounts

    'chat.apps.ChatConfig',  # Chat application for real-time communication
    'payment.apps.PaymentConfig',  # Payment application for processing transactions
    'account.apps.AccountConfig',  # Account application for user management
    'shipping.apps.ShippingConfig',
    'sms.apps.SmsConfig',
]

# Combine all applications into the INSTALLED_APPS setting
INSTALLED_APPS = ['daphne'] + DJANGO_APPS + THIRD_PARTY_APPS + CUSTOM_APPS

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'cart.middleware.CartSessionMiddleware',  # Add custom cart session middleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'ecommerce_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce_api.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'account.UserAccount'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'EXCEPTION_HANDLER': 'ecommerce_api.core.exceptions.custom_exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'ecommerce_api.utils.pagination.CustomPageNumberPagination',
    'DEFAULT_RENDERER_CLASSES': [
        'ecommerce_api.core.renderers.ApiResponseRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '400/day',
        'user': '1000/day',
    },
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

# JWT Authentication Tokens
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=env.int('JWT_ACCESS_TOKEN_LIFETIME_DAYS', 1)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7)),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# API Documentation Settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Hypex eCommerce API Documentation",
    "DESCRIPTION": "A scalable RESTful eCommerce API using Django, JWT auth, Redis caching, Celery for task scheduling, advanced search, tagging, and personalized results.",
    "VERSION": "1.2.6",
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
INTERNAL_IPS = env.list('INTERNAL_IPS', default=['127.0.0.1', 'localhost'])

CART_SESSION_ID = 'cart'
SITE_ID = 1
ASGI_APPLICATION = 'ecommerce_api.asgi.application'

SMS_IR_OTP_TEMPLATE_ID = env.int('SMS_IR_OTP_TEMPLATE_ID', 123456)

POSTEX_SENDER_NAME = env('POSTEX_SENDER_NAME', default='Your Company Name')
POSTEX_SENDER_PHONE = env('POSTEX_SENDER_PHONE', default='Your Company Phone')
POSTEX_SENDER_ADDRESS = env('POSTEX_SENDER_ADDRESS', default='Your Company Address')
POSTEX_SENDER_POSTAL_CODE = env('POSTEX_SENDER_POSTAL_CODE', default='Your Company Postal Code')
POSTEX_FROM_CITY_CODE = env.int('POSTEX_FROM_CITY_CODE', default=1)
POSTEX_SERVICE_TYPE = env('POSTEX_SERVICE_TYPE', default='standard')

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.google.GoogleOAuth2',
]

# Social Auth settings for Google OAuth2
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env('GOOGLE_OAUTH2_KEY', default=None)
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env('GOOGLE_OAUTH2_SECRET', default=None)

DJOSER = {
    'HIDE_USERS': True,
    'EMAIL': {
        'activation': 'account.emails.CustomActivationEmail',
    },
    'SERIALIZERS': {
        'user_create': 'users.api.serializers.UserProfileSerializer',
        'user_delete': 'djoser.serializers.UserDeleteSerializer',
    },
    'LOGIN_FIELD': 'email',
    'SEND_ACTIVATION_EMAIL': True,
    'SEND_CONFIRMATION_EMAIL': True,
    'ACTIVATION_URL': 'auth/activate/{uid}/{token}',
    'PASSWORD_RESET_CONFIRM_URL': 'password/reset/confirm/{uid}/{token}',
    'USERNAME_RESET_CONFIRM_URL': 'username/reset/confirm/{uid}/{token}',
    'PASSWORD_RESET_SHOW_EMAIL': True,
    'USERNAME_CHANGED_EMAIL_CONFIRMATION': True,
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': True,
    'USER_CREATE_PASSWORD_RETYPE': True,
}

LOGIN_URL = reverse_lazy('auth:jwt-create')
USERNAME_FIELD = 'email'

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\"",
        }
    },
    'USE_SESSION_AUTH': False,
}


TAGGIT_CASE_INSENSITIVE = True

# Zibal Payment Gateway
ZIBAL_MERCHANT_ID = env('ZIBAL_MERCHANT_ID')
ZIBAL_WEBHOOK_SECRET = env('ZIBAL_WEBHOOK_SECRET')
ZIBAL_ALLOWED_IPS = env.list('ZIBAL_ALLOWED_IPS', default=['127.0.0.1'])

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULE = {
    'cancel-pending-orders': {
        'task': 'orders.tasks.cancel_pending_orders',
        'schedule': env.float('CANCEL_PENDING_ORDERS_INTERVAL', 600.0),  # Default to 10 minutes
    },
}

# Session cookie settings
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = True

# CSRF settings
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)

# OpenTelemetry settings
OTEL_SERVICE_NAME = env('OTEL_SERVICE_NAME', default='ecommerce-api')
OTEL_EXPORTER_OTLP_ENDPOINT = env('OTEL_EXPORTER_OTLP_ENDPOINT', default='http://jaeger:4318')

if OTEL_EXPORTER_OTLP_ENDPOINT:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.sdk.resources import Resource

    resource = Resource(attributes={
        "service.name": OTEL_SERVICE_NAME
    })

    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces"))
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    DjangoInstrumentor().instrument()
