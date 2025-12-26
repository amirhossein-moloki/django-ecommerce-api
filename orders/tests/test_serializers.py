import pytest
from django.test import RequestFactory
from rest_framework.exceptions import ValidationError

from account.tests.factories import UserFactory, AddressFactory
from cart.cart import Cart
from orders.serializers import OrderCreateSerializer
from shop.tests.factories import ProductVariantFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_request():
    """
    Fixture to create a mock request object with a user and a cart.
    """
    user = UserFactory()
    address = AddressFactory(user=user)
    factory = RequestFactory()
    request = factory.post("/fake-url/")
    request.user = user
    request.session = {}
    cart = Cart(request)
    request.cart = cart
    return request, user, address, cart


def test_order_create_serializer_valid(mock_request):
    """
    Test that the OrderCreateSerializer is valid with correct data.
    """
    request, user, address, cart = mock_request
    variant = ProductVariantFactory(stock=10)
    cart.add(variant, quantity=2)

    data = {"address_id": address.id, "discount_code": ""}
    serializer = OrderCreateSerializer(data=data, context={"request": request})

    assert serializer.is_valid(raise_exception=True)


def test_order_create_serializer_insufficient_stock(mock_request):
    """
    Test that the serializer raises a ValidationError if stock is insufficient.
    """
    request, user, address, cart = mock_request
    variant = ProductVariantFactory(stock=5)
    cart.add(variant, quantity=10)  # Requesting more than available

    data = {"address_id": address.id}
    serializer = OrderCreateSerializer(data=data, context={"request": request})

    with pytest.raises(ValidationError) as excinfo:
        serializer.is_valid(raise_exception=True)
        serializer.save()  # Validation happens in .save() for stock check
    assert f"Not enough stock for {variant.product.name}" in str(excinfo.value)


def test_order_create_serializer_invalid_address(mock_request):
    """
    Test that the serializer raises a ValidationError for an invalid address_id.
    """
    request, user, address, cart = mock_request
    variant = ProductVariantFactory(stock=10)
    cart.add(variant, quantity=1)

    # An address ID that does not exist or belong to the user
    invalid_address_id = 99999

    data = {"address_id": invalid_address_id}
    serializer = OrderCreateSerializer(data=data, context={"request": request})

    with pytest.raises(ValidationError) as excinfo:
        serializer.is_valid(raise_exception=True)
    assert "The selected address is invalid." in str(excinfo.value)


def test_order_create_serializer_empty_cart(mock_request):
    """
    Test that the serializer raises a ValidationError if the cart is empty.
    """
    request, user, address, cart = mock_request
    # Cart is empty by default here

    data = {"address_id": address.id}
    serializer = OrderCreateSerializer(data=data, context={"request": request})

    serializer.is_valid(raise_exception=True)

    with pytest.raises(ValidationError) as excinfo:
        serializer.save()
    assert "Your cart is empty." in str(excinfo.value)
