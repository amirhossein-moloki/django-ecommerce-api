from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from account.tests.factories import UserFactory
from cart.cart import Cart
from orders import services
from orders.models import Order
from orders.tests.factories import OrderFactory
from shop.tests.factories import ProductVariantFactory

pytestmark = pytest.mark.django_db


def test_get_user_orders_for_regular_user():
    """
    Test that a regular user can only see their own orders.
    """
    user1 = UserFactory()
    user2 = UserFactory()
    OrderFactory(user=user1)
    OrderFactory(user=user2)

    orders = services.get_user_orders(user=user1)
    assert orders.count() == 1
    assert orders.first().user == user1


def test_get_user_orders_for_staff_user():
    """
    Test that a staff user can see all orders.
    """
    user1 = UserFactory()
    staff_user = UserFactory(is_staff=True)
    OrderFactory(user=user1)
    OrderFactory(user=staff_user)

    orders = services.get_user_orders(user=staff_user)
    assert orders.count() == 2


from account.tests.factories import AddressFactory


@patch("orders.services.send_order_confirmation_email.delay")
def test_create_order_success(mock_send_email):
    """
    Test successful order creation and that the confirmation email task is called.
    """
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=20)

    # Mock request and cart
    factory = RequestFactory()
    request = factory.post("/fake-url/")
    request.user = user
    request.session = {}
    cart = Cart(request)
    cart.add(variant, quantity=2)
    request.cart = cart  # Attach cart to request for the serializer context

    validated_data = {
        "address_id": address.id,
        "discount_code": "",
    }

    # Execute the service function
    order = services.create_order(request=request, validated_data=validated_data)

    # Assertions
    assert Order.objects.count() == 1
    assert order.user == user
    assert order.items.count() == 1
    assert order.items.first().quantity == 2

    # Check that stock was reduced
    variant.refresh_from_db()
    assert variant.stock == 18

    # Check that the cart was cleared
    assert len(cart) == 0

    # Check that email task was called
    mock_send_email.assert_called_once_with(order.order_id)
