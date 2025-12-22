import asyncio
import uuid
import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from ecommerce_api.asgi import application
from shop.factories import ProductFactory, UserFactory
from chat.models import Message

pytestmark = [pytest.mark.django_db, pytest.mark.asyncio]


class TestChatConsumer:
    async def test_connect_authenticated_user_and_valid_product(self):
        user = await sync_to_async(UserFactory)()
        product = await sync_to_async(ProductFactory)()
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/room/{product.product_id}/"
        )
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_reject_unauthenticated_user(self):
        product = await sync_to_async(ProductFactory)()
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/room/{product.product_id}/"
        )
        connected, close_code = await communicator.connect()
        assert not connected
        assert close_code == 1000  # Normal closure

    async def test_reject_non_existent_product(self):
        user = await sync_to_async(UserFactory)()
        non_existent_uuid = uuid.uuid4()
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/room/{non_existent_uuid}/"
        )
        communicator.scope["user"] = user
        connected, close_code = await communicator.connect()
        assert not connected
        assert close_code == 1000  # Normal closure

    async def test_buyer_sends_message_to_seller(self):
        buyer = await sync_to_async(UserFactory)()
        seller = await sync_to_async(UserFactory)()
        product = await sync_to_async(ProductFactory)(user=seller)
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/room/{product.product_id}/"
        )
        communicator.scope["user"] = buyer
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello, seller!"})

        # Check for the confirmation message to the sender
        response = await communicator.receive_json_from()
        assert response["type"] == "message_sent"
        assert "message_id" in response

        # Verify the message was saved in the database
        message_exists = await sync_to_async(Message.objects.filter(
            sender=buyer,
            recipient=seller,
            product=product,
            content="Hello, seller!"
        ).exists)()
        assert message_exists

        await communicator.disconnect()

    async def test_seller_sends_message_to_buyer(self):
        buyer = await sync_to_async(UserFactory)()
        seller = await sync_to_async(UserFactory)()
        product = await sync_to_async(ProductFactory)(user=seller)

        communicator = WebsocketCommunicator(
            application, f"/ws/chat/room/{product.product_id}/"
        )
        communicator.scope["user"] = seller
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to(
            {"message": "Hello, buyer!", "recipient": buyer.username}
        )

        # Check for the confirmation message to the sender (seller)
        response = await communicator.receive_json_from()
        assert response["type"] == "message_sent"

        # Verify the message was saved in the database
        message_exists = await sync_to_async(Message.objects.filter(
            sender=seller,
            recipient=buyer,
            product=product,
            content="Hello, buyer!"
        ).exists)()
        assert message_exists

        await communicator.disconnect()

    async def test_receive_invalid_json(self):
        user = await sync_to_async(UserFactory)()
        product = await sync_to_async(ProductFactory)()
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/room/{product.product_id}/"
        )
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_to(text_data="not a valid json")
        response = await communicator.receive_json_from()
        assert response["error"] == "Invalid JSON format"
        await communicator.disconnect()

    async def test_receive_message_with_empty_content(self):
        user = await sync_to_async(UserFactory)()
        product = await sync_to_async(ProductFactory)()
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/room/{product.product_id}/"
        )
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_json_to({"message": ""})
        response = await communicator.receive_json_from()
        assert response["error"] == "Message content is required"
        await communicator.disconnect()

    async def test_receive_message_too_long(self):
        user = await sync_to_async(UserFactory)()
        product = await sync_to_async(ProductFactory)()
        communicator = WebsocketCommunicator(
            application, f"/ws/chat/room/{product.product_id}/"
        )
        communicator.scope["user"] = user
        await communicator.connect()

        long_message = "a" * 1001
        await communicator.send_json_to({"message": long_message})
        response = await communicator.receive_json_from()
        assert response["error"] == "Message too long. Maximum 1000 characters allowed."
        await communicator.disconnect()
