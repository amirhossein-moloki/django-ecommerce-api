import json
import os

import django
import pytest
import requests
from django.core.management import call_command
from django.test.utils import (
    setup_databases,
    setup_test_environment,
    teardown_databases,
    teardown_test_environment,
)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce_api.settings.test")
django.setup()


@pytest.fixture(scope="session", autouse=True)
def django_test_environment():
    setup_test_environment()
    db_cfg = setup_databases(verbosity=0, interactive=False, keepdb=False)
    yield
    teardown_databases(db_cfg, verbosity=0)
    teardown_test_environment()


@pytest.fixture(autouse=True)
def flush_db():
    yield
    call_command("flush", verbosity=0, interactive=False)


class RequestsMock:
    def __init__(self):
        self._registry = {}

    def post(self, url, json=None, status_code=200, exc=None):
        self._registry[("POST", url)] = {
            "json": json,
            "status_code": status_code,
            "exc": exc,
        }

    def _handle(self, method, url):
        key = (method.upper(), url)
        if key not in self._registry:
            raise AssertionError(f"No mock registered for {method} {url}")
        spec = self._registry[key]
        if spec["exc"] is not None:
            exc = spec["exc"]
            if isinstance(exc, type):
                raise exc()
            raise exc
        response = requests.Response()
        response.status_code = spec["status_code"]
        response.url = url
        if spec["json"] is not None:
            response._content = json.dumps(spec["json"]).encode("utf-8")
            response.headers["Content-Type"] = "application/json"
        else:
            response._content = b""
        return response


@pytest.fixture
def requests_mock(monkeypatch):
    mocker = RequestsMock()

    def _post(self, url, **kwargs):
        return mocker._handle("POST", url)

    monkeypatch.setattr(requests.Session, "post", _post)
    return mocker
