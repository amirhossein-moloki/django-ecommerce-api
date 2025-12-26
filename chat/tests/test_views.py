import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from account.tests.factories import UserFactory
from chat.factories import MessageFactory
from shop.tests.factories import ProductFactory


@pytest.fixture
def api_client():
    return APIClient()


def test_product_chat_view_filters_messages_by_owner(api_client):
    seller = UserFactory()
    buyer = UserFactory()
    other_sender = UserFactory()
    other_recipient = UserFactory()
    product = ProductFactory(user=seller)
    MessageFactory(
        sender=buyer, recipient=seller, product=product, content="allowed message"
    )
    MessageFactory(
        sender=other_sender,
        recipient=other_recipient,
        product=product,
        content="blocked message",
    )

    api_client.force_authenticate(user=seller)
    url = reverse("api-v1:product-chat", kwargs={"product_id": product.product_id})
    response = api_client.get(url)

    assert response.status_code == 200
    messages = response.data["data"]["messages"]
    contents = [message["content"] for message in messages]
    assert contents == ["allowed message"]
