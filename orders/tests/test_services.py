from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import RequestFactory
from rest_framework.exceptions import ValidationError

from account.tests.factories import AddressFactory, UserFactory
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
    staff_user = UserFactory()
    staff_user.is_staff = True
    staff_user.save(update_fields=["is_staff"])
    OrderFactory(user=user1)
    OrderFactory(user=staff_user)

    orders = services.get_user_orders(user=staff_user)
    assert orders.count() == 2


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


@patch("orders.serializers.DiscountService")
@patch("orders.services.send_order_confirmation_email.delay")
def test_create_order_with_valid_discount_code(
    mock_send_email, mock_discount_service
):
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=20)

    factory = RequestFactory()
    request = factory.post("/fake-url/")
    request.user = user
    request.session = {}
    cart = Cart(request)
    cart.add(variant, quantity=1)
    request.cart = cart

    mock_discount_service.get_applicable_discounts.return_value.exists.return_value = (
        True
    )
    mock_discount_service.apply_discount.return_value = (Decimal("0.00"), None)

    validated_data = {"address_id": address.id, "discount_code": "SAVE10"}

    order = services.create_order(request=request, validated_data=validated_data)

    assert order.discount_amount == Decimal("0.00")
    mock_discount_service.get_applicable_discounts.assert_called_once_with(
        cart, user, discount_code="SAVE10"
    )
    mock_discount_service.apply_discount.assert_called_once_with(
        cart, user, "SAVE10"
    )
    mock_send_email.assert_called_once_with(order.order_id)


@patch("orders.serializers.DiscountService")
def test_create_order_with_invalid_discount_code_raises(mock_discount_service):
    user = UserFactory()
    address = AddressFactory(user=user)

    factory = RequestFactory()
    request = factory.post("/fake-url/")
    request.user = user
    request.session = {}
    cart = Cart(request)
    request.cart = cart

    mock_discount_service.get_applicable_discounts.return_value.exists.return_value = (
        False
    )

    validated_data = {"address_id": address.id, "discount_code": "BADCODE"}

    with pytest.raises(ValidationError) as excinfo:
        services.create_order(request=request, validated_data=validated_data)

    assert "discount code is invalid" in str(excinfo.value).lower()


@patch("orders.serializers.DiscountService.apply_discount")
@patch("orders.services.send_order_confirmation_email.delay")
def test_create_order_does_not_send_email_in_test_mode(
    mock_send_email, mock_apply_discount
):
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=5)

    factory = RequestFactory()
    request = factory.post("/fake-url/")
    request.user = user
    request.session = {}
    cart = Cart(request)
    cart.add(variant, quantity=1)
    request.cart = cart

    mock_apply_discount.return_value = (Decimal("0.00"), None)

    with patch.object(services.sys, "argv", ["manage.py", "test"]):
        services.create_order(
            request=request, validated_data={"address_id": address.id}
        )

    mock_send_email.assert_not_called()


@patch("orders.serializers.DiscountService.apply_discount")
@patch("orders.services.send_order_confirmation_email.delay")
def test_create_order_sends_email_when_not_in_test_mode(
    mock_send_email, mock_apply_discount
):
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=5)

    factory = RequestFactory()
    request = factory.post("/fake-url/")
    request.user = user
    request.session = {}
    cart = Cart(request)
    cart.add(variant, quantity=1)
    request.cart = cart

    mock_apply_discount.return_value = (Decimal("0.00"), None)

    with patch.object(services.sys, "argv", ["manage.py", "runserver"]):
        order = services.create_order(
            request=request, validated_data={"address_id": address.id}
        )

    mock_send_email.assert_called_once_with(order.order_id)
