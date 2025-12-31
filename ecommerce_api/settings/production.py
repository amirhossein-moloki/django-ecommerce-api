from .base import *

# Production-specific settings
# -----------------------------------------------------------------------------
# SECURITY SETTINGS
# Ensure the application is served securely in a production environment.
# -----------------------------------------------------------------------------

# Force SSL redirection.
# The 'SECURE_PROXY_SSL_HEADER' tells Django to trust the X-Forwarded-Proto
# header from the proxy (Nginx), which is crucial for correct HTTPS detection.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

# Mark session and CSRF cookies as secure.
# This ensures they are only sent over HTTPS connections, mitigating the
# risk of session hijacking via man-in-the-middle attacks.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTP Strict Transport Security (HSTS)
# Instructs browsers to always connect to the site via HTTPS for the next year.
# This reduces the impact of SSL-stripping attacks.
# The `includeSubDomains` and `preload` directives enhance this protection.
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
USE_X_FORWARDED_HOST = True

# Session settings for production
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Channel layers for real-time features in production
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Logging configuration for production
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json_formatter": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json_formatter",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# Ensure debug_toolbar is not included in production
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]
MIDDLEWARE = [m for m in MIDDLEWARE if "debug_toolbar" not in m]
