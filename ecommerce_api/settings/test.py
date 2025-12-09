import os

# Set dummy environment variables for testing before importing base settings
os.environ.setdefault('SECRET_KEY', 'dummy-secret-key-for-testing')
os.environ.setdefault('DEBUG', 'False')
os.environ.setdefault('ALLOWED_HOSTS', 'testserver')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/1')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://localhost:6379/0')
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
os.environ.setdefault('EMAIL_URL', 'consolemail://')
os.environ.setdefault('GOOGLE_OAUTH2_KEY', 'dummy-key')
os.environ.setdefault('GOOGLE_OAUTH2_SECRET', 'dummy-secret')
os.environ.setdefault('ZIBAL_MERCHANT_ID', 'dummy-zibal-merchant')
os.environ.setdefault('ZIBAL_WEBHOOK_SECRET', 'dummy-zibal-secret')
os.environ.setdefault('SMS_IR_OTP_TEMPLATE_ID', '123456')

from .base import *

# Override settings for a predictable test environment

# Use dummy cache for tests to avoid side effects
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Use in-memory channel layer for tests
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Use a database-backed session engine for tests
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Make Celery tasks execute synchronously for tests
CELERY_TASK_ALWAYS_EAGER = True

# Disable logging during tests to keep the output clean
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
}
