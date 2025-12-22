import pytest
from django.core.cache import caches
from rest_framework.test import APIClient
from account.factories import UserFactory


def pytest_configure():
    # ... any project-wide test configuration ...
    pass


@pytest.fixture(autouse=True)
def clear_cache_before_each_test():
    """
    Fixture to clear the default Django cache before each test.
    This prevents state from leaking between tests, especially for
    features like rate-limiting that rely on the cache.
    """
    caches["default"].clear()
    yield


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client
