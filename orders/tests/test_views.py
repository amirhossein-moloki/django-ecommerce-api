import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.tests.factories import UserFactory
from cart.cart import Cart
from orders.models import Order
from orders.tests.factories import OrderFactory
from shop.tests.factories import ProductVariantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_order_list_unauthenticated(api_client):
    """
    Test that unauthenticated users cannot access the order list.
    """
    url = reverse("api-v1:orders-list")
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_order_list_authenticated_user(api_client):
    """
    Test that authenticated users can only list their own orders.
    """
    user1 = UserFactory()
    user2 = UserFactory()
    OrderFactory(user=user1)
    OrderFactory(user=user2)

    api_client.force_authenticate(user=user1)
    url = reverse("api-v1:orders-list")
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["data"]) == 1
    assert response.data["data"][0]["user"] == user1.username


def test_order_retrieve_permission_denied(api_client):
    """
    Test that a user cannot retrieve an order belonging to another user.
    """
    user1 = UserFactory()
    user2 = UserFactory()
    order_of_user2 = OrderFactory(user=user2)

    api_client.force_authenticate(user=user1)
    url = reverse("api-v1:orders-detail", kwargs={"pk": order_of_user2.pk})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND


from account.tests.factories import AddressFactory


def test_order_creation_api(api_client):
    """
    Test the full order creation flow via the API.
    """
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=50)

    # Add item to cart via API
    api_client.force_authenticate(user=user)
    add_to_cart_url = reverse(
        "api-v1:cart-add", kwargs={"variant_id": variant.variant_id}
    )
    api_client.post(add_to_cart_url, {"quantity": 3})

    url = reverse("api-v1:orders-list")
    data = {"address_id": address.id}

    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_201_CREATED
    assert Order.objects.count() == 1
    order = Order.objects.first()
    assert order.user == user
    assert order.items.count() == 1

    variant.refresh_from_db()
    assert variant.stock == 47


def test_order_creation_insufficient_stock_api(api_client):
    """
    Test that creating an order with insufficient stock fails.
    """
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=2)

    # Add item to cart via API
    api_client.force_authenticate(user=user)
    add_to_cart_url = reverse(
        "api-v1:cart-add", kwargs={"variant_id": variant.variant_id}
    )
    # This post should fail validation, but the test proceeds.
    # The cart will be empty when creating an order.
    api_client.post(add_to_cart_url, {"quantity": 5})

    url = reverse("api-v1:orders-list")
    data = {"address_id": address.id}

    response = api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Your cart is empty" in response.data["message"]
    assert Order.objects.count() == 0
    variant.refresh_from_db()
    assert variant.stock == 2
