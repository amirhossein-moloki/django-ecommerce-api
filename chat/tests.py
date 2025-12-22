import pytest
from django.urls import reverse
from rest_framework import status
# from channels.testing import WebsocketCommunicator
# from ecommerce_api.asgi import application
from shop.factories import ProductFactory, UserFactory
from .factories import MessageFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    return ProductFactory.create()


@pytest.fixture
def user1():
    return UserFactory.create()


@pytest.fixture
def user2():
    return UserFactory.create()


class TestMessageModel:
    def test_message_creation(self, user1, user2, product):
        message = MessageFactory.create(sender=user1, recipient=user2, product=product)
        assert message.sender == user1
        assert message.content is not None


class TestProductChatAPI:
    def test_get_chat_messages_unauthenticated(self, api_client, product):
        url = reverse('api-v1:product-chat', kwargs={'product_id': product.product_id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_chat_messages_authenticated(self, api_client, user1, user2, product):
        MessageFactory.create_batch(5, sender=user1, recipient=user2, product=product)
        api_client.force_authenticate(user=user1)
        url = reverse('api-v1:product-chat', kwargs={'product_id': product.product_id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['messages']) == 5


# @pytest.mark.asyncio
# class TestChatConsumer:
#     async def test_connect_authenticated(self, user1, product):
#         communicator = WebsocketCommunicator(application, f"/ws/chat/{product.product_id}/")
#         communicator.scope['user'] = user1
#         connected, _ = await communicator.connect()
#         assert connected
#         await communicator.disconnect()

#     async def test_receive_message(self, user1, user2, product):
#         communicator = WebsocketCommunicator(application, f"/ws/chat/{product.product_id}/")
#         communicator.scope['user'] = user1
#         await communicator.connect()

#         await communicator.send_json_to({'message': 'Hello, world!', 'recipient': user2.username})
#         response = await communicator.receive_json_from()

#         assert response['sender'] == user1.username
#         assert response['message'] == 'Hello, world!'
#         await communicator.disconnect()
