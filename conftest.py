import os
import django
import pytest
from django.conf import settings
from rest_framework.test import APIClient
from account.factories import UserFactory

def pytest_configure():
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_api.settings.test')
        django.setup()

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def api_client():
    return APIClient()
