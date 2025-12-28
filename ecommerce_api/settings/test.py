from .base import *

# Override settings for testing

# Use a faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Remove optional dev-only apps/middleware that are not installed in tests
INSTALLED_APPS = [
    app for app in INSTALLED_APPS if app not in ["debug_toolbar", "django_extensions"]
]
MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE
    if middleware != "debug_toolbar.middleware.DebugToolbarMiddleware"
]

# Use file-based database for tests to support async threads
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",
    }
}

# Use in-memory cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable Celery for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "db+sqlite:///celery-results.sqlite"

# Simplify logging for tests
LOGGING = {}

# Set TESTING flag
TESTING = True
DEBUG = False

# Zibal test credentials
ZIBAL_MERCHANT_ID = "zibal"
ZIBAL_WEBHOOK_SECRET = "a-secret-for-zibal-webhooks"
