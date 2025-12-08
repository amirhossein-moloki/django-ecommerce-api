from .base import *

# Set a dummy secret key for the test environment
SECRET_KEY = 'dummy-secret-key-for-testing'
DEBUG = False
ALLOWED_HOSTS = ['testserver']

# Use dummy cache for tests to avoid side effects
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Use in-memory SQLite database for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Use in-memory channel layer for tests
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Use console backend for emails in tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Since we're not using redis for tests, we need to make sure the session engine is not set to cache
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Dummy social auth keys for tests
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = 'dummy-key'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = 'dummy-secret'

# Dummy domain and site name for tests
DOMAIN = 'localhost:8000'
SITE_NAME = 'Test Site'

# Make celery tasks eager in tests
CELERY_TASK_ALWAYS_EAGER = True

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
}

# Dummy Redis URL for the recommender system
REDIS_URL = 'redis://localhost:6379/1'
