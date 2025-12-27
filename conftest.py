import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests
from django.conf import settings as django_settings
from django.core.management import call_command


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce_api.settings.test")


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    return db


@pytest.fixture(autouse=True)
def flush_db(db):
    yield
    call_command("flush", verbosity=0, interactive=False)


class SettingsWrapper:
    def __init__(self, settings):
        self._settings = settings
        self._original = {}

    def __getattr__(self, name):
        return getattr(self._settings, name)

    def __setattr__(self, name, value):
        if name in {"_settings", "_original"}:
            return super().__setattr__(name, value)
        if name not in self._original:
            self._original[name] = (getattr(self._settings, name, None), hasattr(self._settings, name))
        setattr(self._settings, name, value)

    def __delattr__(self, name):
        if name not in self._original:
            self._original[name] = (getattr(self._settings, name, None), hasattr(self._settings, name))
        delattr(self._settings, name)

    def restore(self):
        for name, (value, existed) in self._original.items():
            if existed:
                setattr(self._settings, name, value)
            else:
                delattr(self._settings, name)


@pytest.fixture
def settings():
    wrapper = SettingsWrapper(django_settings)
    yield wrapper
    wrapper.restore()


@pytest.fixture
def mocker():
    patches = []

    def _patch(target, *args, **kwargs):
        patcher = patch(target, *args, **kwargs)
        patched = patcher.start()
        patches.append(patcher)
        return patched

    yield SimpleNamespace(patch=_patch)
    for patcher in reversed(patches):
        patcher.stop()


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
