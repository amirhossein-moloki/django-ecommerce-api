
from .base import *

# Override settings for testing

# Use a faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use in-memory database for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
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
