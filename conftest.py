import os

import django
import pytest
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
