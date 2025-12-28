import os
import tempfile
import uuid

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.db import connections

from account.tests.factories import UserFactory
from chat.models import Message
from chat.routing import websocket_urlpatterns
from shop.tests.factories import ProductFactory


@pytest.fixture
def websocket_application():
    original_layers = getattr(django_settings, "CHANNEL_LAYERS", None)
    channel_layers = original_layers or {}
    backend = channel_layers.get("default", {}).get("BACKEND", "")
    if not channel_layers or "redis" in backend.lower():
        django_settings.CHANNEL_LAYERS = {
            "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
        }
    try:
        yield URLRouter(websocket_urlpatterns)
    finally:
        if original_layers is None:
            del django_settings.CHANNEL_LAYERS
        else:
            django_settings.CHANNEL_LAYERS = original_layers


@pytest.fixture(scope="module", autouse=True)
def file_based_database():
    if django_settings.DATABASES["default"]["NAME"] != ":memory:":
        yield
        return

    original_db = django_settings.DATABASES["default"].copy()
    temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    temp_db.close()
    django_settings.DATABASES["default"]["NAME"] = temp_db.name
    connections.databases["default"] = django_settings.DATABASES["default"]
    connections.close_all()
    call_command("migrate", verbosity=0, interactive=False)
    try:
        yield
    finally:
        connections.close_all()
        django_settings.DATABASES["default"] = original_db
        connections.databases["default"] = original_db
        os.unlink(temp_db.name)


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def seller():
    return UserFactory()


@pytest.fixture
def buyer():
    return UserFactory()


@pytest.fixture
def product():
    return ProductFactory()


@pytest.fixture
def product_with_seller(seller):
    return ProductFactory(user=seller)


@pytest.fixture(autouse=True)
def allow_async_db(monkeypatch):
    monkeypatch.setenv("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_connect_allows_authenticated_user(websocket_application, product, user):
    communicator = WebsocketCommunicator(
        websocket_application, f"/ws/chat/room/{product.product_id}/"
    )
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected is True
    await communicator.disconnect()


@pytest.mark.anyio
async def test_connect_rejects_anonymous_user(websocket_application, product):
    communicator = WebsocketCommunicator(
        websocket_application, f"/ws/chat/room/{product.product_id}/"
    )
    communicator.scope["user"] = AnonymousUser()
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.anyio
async def test_connect_rejects_invalid_product(websocket_application, user):
    communicator = WebsocketCommunicator(
        websocket_application, f"/ws/chat/room/{uuid.uuid4()}/"
    )
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.anyio
async def test_send_message_broadcasts_and_persists(
    websocket_application, product_with_seller, seller, buyer
):
    communicator = WebsocketCommunicator(
        websocket_application, f"/ws/chat/room/{product_with_seller.product_id}/"
    )
    communicator.scope["user"] = buyer
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to({"message": "Hello from buyer"})
    responses = [
        await communicator.receive_json_from(),
        await communicator.receive_json_from(),
    ]

    broadcast = next(item for item in responses if "message" in item)
    confirmation = next(
        item for item in responses if item.get("type") == "message_sent"
    )

    assert broadcast["message"] == "Hello from buyer"
    assert broadcast["sender"] == buyer.username
    assert confirmation["message_id"] is not None

    saved_message = Message.objects.get(id=confirmation["message_id"])
    assert saved_message.content == "Hello from buyer"
    assert saved_message.sender == buyer
    assert saved_message.recipient == seller
    assert saved_message.product == product_with_seller

    await communicator.disconnect()


@pytest.mark.anyio
async def test_send_empty_message_returns_error(websocket_application, product, user):
    communicator = WebsocketCommunicator(
        websocket_application, f"/ws/chat/room/{product.product_id}/"
    )
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to({"message": "   "})
    response = await communicator.receive_json_from()
    assert response["error"] == "Message content is required"

    await communicator.disconnect()


@pytest.mark.anyio
async def test_send_too_long_message_returns_error(
    websocket_application, product, user
):
    communicator = WebsocketCommunicator(
        websocket_application, f"/ws/chat/room/{product.product_id}/"
    )
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to({"message": "a" * 1001})
    response = await communicator.receive_json_from()
    assert response["error"] == "Message too long. Maximum 1000 characters allowed."

    await communicator.disconnect()


@pytest.mark.anyio
async def test_seller_without_recipient_returns_error(
    websocket_application, product_with_seller, seller
):
    communicator = WebsocketCommunicator(
        websocket_application, f"/ws/chat/room/{product_with_seller.product_id}/"
    )
    communicator.scope["user"] = seller
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to({"message": "Seller message"})
    response = await communicator.receive_json_from()
    assert (
        response["error"] == "Recipient username is required when seller sends message"
    )

    await communicator.disconnect()
