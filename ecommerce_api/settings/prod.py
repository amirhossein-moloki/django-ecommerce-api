from .base import *

DEBUG = False

ADMINS = [
    ('Yousef Y', 'hypexstore@gmail.com'),
]

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['eCommerce.com', 'www.eCommerce.com', 'web'])

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
