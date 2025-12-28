import importlib.util

from .base import INSTALLED_APPS, MIDDLEWARE

# Development-specific settings
INSTALLED_APPS += ["django_extensions"]

if importlib.util.find_spec("debug_toolbar"):
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE = [
        *MIDDLEWARE[:2],
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        *MIDDLEWARE[2:],
    ]
