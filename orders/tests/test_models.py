import pytest
from django.core.exceptions import ValidationError
from account.tests.factories import UserFactory, AddressFactory
from orders.models import Order
from shop.tests.factories import ProductVariantFactory

pytestmark = pytest.mark.django_db


def test_order_creation():
    """
    Test that an Order and OrderItem can be created successfully.
    """
    user = UserFactory()
    address = AddressFactory(user=user)
    variant = ProductVariantFactory(stock=10)

    order = Order.objects.create(user=user, address=address)
    order.items.create(
        variant=variant,
        quantity=2,
        price=variant.price,
        product_name=variant.product.name,
        product_sku=variant.sku,
    )

    assert order.pk is not None
    assert order.items.count() == 1
    item = order.items.first()
    assert item.quantity == 2
    assert item.price == variant.price
    assert str(order) == f"Order: {order.order_id} by {user.username}"
    assert (
        str(item) == f"Order Item: {variant.product.name} (Order ID: {order.order_id})"
    )


def test_order_state_machine_valid_transitions():
    """
    Test valid state transitions for the Order model.
    """
    order = Order.objects.create(user=UserFactory())
    assert order.status == Order.Status.PENDING

    # PENDING -> PAID
    order.status = Order.Status.PAID
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.PAID

    # PAID -> PROCESSING
    order.status = Order.Status.PROCESSING
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.PROCESSING

    # PROCESSING -> SHIPPED
    order.status = Order.Status.SHIPPED
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.SHIPPED

    # SHIPPED -> DELIVERED
    order.status = Order.Status.DELIVERED
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.DELIVERED


def test_order_state_machine_invalid_transition():
    """
    Test that an invalid state transition raises a ValidationError.
    """
    order = Order.objects.create(user=UserFactory(), status=Order.Status.PENDING)
    with pytest.raises(ValidationError) as excinfo:
        order.status = Order.Status.SHIPPED
        order.save()
    assert "Invalid state transition" in str(excinfo.value)


def test_order_cancellation_from_pending():
    """
    Test that an order can be canceled from the PENDING state.
    """
    order = Order.objects.create(user=UserFactory(), status=Order.Status.PENDING)
    order.status = Order.Status.CANCELED
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELED


def test_restore_stock_on_cancel():
    """
    Test that product stock is restored when an order is canceled.
    """
    variant = ProductVariantFactory(stock=10)
    order = Order.objects.create(user=UserFactory(), status=Order.Status.PAID)
    order.items.create(variant=variant, quantity=3, price=variant.price)

    # Simulate stock reduction during order placement
    variant.stock -= 3
    variant.save()
    variant.refresh_from_db()
    assert variant.stock == 7

    # Cancel the order
    order.status = Order.Status.CANCELED
    order.save()
    variant.refresh_from_db()

    assert variant.stock == 10


def test_no_stock_restore_if_shipped():
    """
    Test that stock is not restored if the order was already shipped.
    """
    variant = ProductVariantFactory(stock=5)
    order = Order.objects.create(user=UserFactory(), status=Order.Status.SHIPPED)
    order.items.create(variant=variant, quantity=2, price=variant.price)

    # Stock would have been 5, now we check if canceling a shipped order restores it
    # The logic in the model should prevent this
    with pytest.raises(ValidationError):
        order.status = Order.Status.CANCELED
        order.save()

    variant.refresh_from_db()
    # Stock should remain unchanged because the transition is invalid
    assert variant.stock == 5
