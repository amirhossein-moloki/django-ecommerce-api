from decimal import Decimal
from unittest.mock import Mock

import pytest
from django.test import RequestFactory

from coupons.factories import CouponFactory
from orders.models import Order
from orders.tests.factories import OrderFactory, OrderItemFactory
from payment.models import PaymentTransaction
from payment.gateways import ZibalGatewayError
from payment.services import process_payment, verify_payment
from shop.tests.factories import ProductVariantFactory


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def add_coupon_attribute(monkeypatch):
    monkeypatch.setattr(Order, "coupon", None, raising=False)


def _build_request(user):
    request = RequestFactory().post("/payment/process/")
    request.user = user
    return request


def _create_order_with_item(user, price=Decimal("250.00"), quantity=2, stock=10):
    order = OrderFactory(user=user)
    variant = ProductVariantFactory(price=price, stock=stock)
    OrderItemFactory(order=order, variant=variant, price=price, quantity=quantity)
    order.calculate_total_payable()
    order.save(update_fields=["subtotal", "total_payable"])
    return order


def test_process_payment_success_creates_transaction(mocker):
    user = OrderFactory().user
    order = _create_order_with_item(user)
    request = _build_request(user)

    mocker.patch(
        "payment.services.ZibalGateway.create_payment_request",
        return_value={"trackId": "track-123", "result": 100},
    )

    payment_url = process_payment(request, order.order_id)

    assert payment_url == "https://gateway.zibal.ir/start/track-123"
    order.refresh_from_db()
    assert order.payment_track_id == "track-123"
    assert order.payment_gateway == "zibal"

    transaction_log = PaymentTransaction.objects.get(order=order)
    assert transaction_log.event_type == PaymentTransaction.EventType.INITIATE
    assert transaction_log.status == PaymentTransaction.Status.PROCESSED
    assert transaction_log.track_id == "track-123"
    assert transaction_log.amount == int(order.total_payable * 100)


def test_process_payment_already_paid_logs_failure():
    user = OrderFactory().user
    order = _create_order_with_item(user)
    order.payment_status = Order.PaymentStatus.SUCCESS
    order.save(update_fields=["payment_status"])
    request = _build_request(user)

    with pytest.raises(ValueError, match="already been paid"):
        process_payment(request, order.order_id)

    transaction_log = PaymentTransaction.objects.get(order=order)
    assert transaction_log.event_type == PaymentTransaction.EventType.INITIATE
    assert transaction_log.status == PaymentTransaction.Status.FAILED


def test_process_payment_insufficient_stock_logs_failure():
    user = OrderFactory().user
    order = _create_order_with_item(user, quantity=5, stock=1)
    request = _build_request(user)

    with pytest.raises(ValueError, match="Insufficient stock"):
        process_payment(request, order.order_id)

    transaction_log = PaymentTransaction.objects.get(order=order)
    assert transaction_log.status == PaymentTransaction.Status.FAILED


def test_process_payment_invalid_coupon_logs_failure(monkeypatch):
    user = OrderFactory().user
    order = _create_order_with_item(user)
    order.coupon = CouponFactory(active=False)
    request = _build_request(user)

    select_for_update = Mock()
    select_for_update.get.return_value = order
    monkeypatch.setattr(
        Order.objects, "select_for_update", Mock(return_value=select_for_update)
    )

    with pytest.raises(ValueError, match="no longer valid"):
        process_payment(request, order.order_id)

    transaction_log = PaymentTransaction.objects.get(order=order)
    assert transaction_log.status == PaymentTransaction.Status.FAILED


def test_process_payment_coupon_usage_limit_logs_failure(monkeypatch):
    user = OrderFactory().user
    order = _create_order_with_item(user)
    order.coupon = CouponFactory(max_usage=1, usage_count=1)
    request = _build_request(user)

    select_for_update = Mock()
    select_for_update.get.return_value = order
    monkeypatch.setattr(
        Order.objects, "select_for_update", Mock(return_value=select_for_update)
    )

    with pytest.raises(ValueError, match="usage limit"):
        process_payment(request, order.order_id)

    transaction_log = PaymentTransaction.objects.get(order=order)
    assert transaction_log.status == PaymentTransaction.Status.FAILED


def test_process_payment_coupon_min_purchase_logs_failure(monkeypatch):
    user = OrderFactory().user
    order = _create_order_with_item(user, price=Decimal("10.00"), quantity=1)
    order.coupon = CouponFactory(min_purchase_amount=Decimal("500.00"))
    request = _build_request(user)

    select_for_update = Mock()
    select_for_update.get.return_value = order
    monkeypatch.setattr(
        Order.objects, "select_for_update", Mock(return_value=select_for_update)
    )

    with pytest.raises(ValueError, match="minimum purchase"):
        process_payment(request, order.order_id)

    transaction_log = PaymentTransaction.objects.get(order=order)
    assert transaction_log.status == PaymentTransaction.Status.FAILED


def test_process_payment_gateway_error_logs_failure(mocker):
    user = OrderFactory().user
    order = _create_order_with_item(user)
    request = _build_request(user)

    mocker.patch(
        "payment.services.ZibalGateway.create_payment_request",
        side_effect=ZibalGatewayError("gateway down"),
    )

    with pytest.raises(ZibalGatewayError, match="gateway down"):
        process_payment(request, order.order_id)

    transaction_log = PaymentTransaction.objects.get(order=order)
    assert transaction_log.status == PaymentTransaction.Status.FAILED


def test_verify_payment_success_updates_order_and_transaction(mocker):
    order = _create_order_with_item(OrderFactory().user)
    order.payment_track_id = "track-456"
    order.save(update_fields=["payment_track_id"])

    response_payload = {
        "result": 100,
        "amount": int(order.total_payable * 100),
        "orderId": str(order.order_id),
        "refNumber": "ref-999",
    }

    mocker.patch(
        "payment.services.ZibalGateway.verify_payment", return_value=response_payload
    )
    delay_mock = mocker.patch("payment.services.create_postex_shipment_task.delay")

    message = verify_payment(
        order.payment_track_id,
        signature="sig",
        ip_address="127.0.0.1",
        raw_payload={"trackId": order.payment_track_id},
    )

    assert "Payment verified successfully" in message
    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.SUCCESS
    assert order.payment_ref_id == "ref-999"
    assert order.status == Order.Status.PAID

    transaction_log = PaymentTransaction.objects.get(
        order=order, event_type=PaymentTransaction.EventType.VERIFY
    )
    assert transaction_log.status == PaymentTransaction.Status.PROCESSED
    assert transaction_log.amount == response_payload["amount"]
    assert transaction_log.ref_id == "ref-999"
    delay_mock.assert_called_once_with(order.order_id)


def test_verify_payment_amount_mismatch_fails(mocker):
    order = _create_order_with_item(OrderFactory().user)
    order.payment_track_id = "track-789"
    order.save(update_fields=["payment_track_id"])

    mocker.patch(
        "payment.services.ZibalGateway.verify_payment",
        return_value={
            "result": 100,
            "amount": int(order.total_payable * 100) + 500,
            "orderId": str(order.order_id),
        },
    )
    delay_mock = mocker.patch("payment.services.create_postex_shipment_task.delay")

    with pytest.raises(ValueError, match="Amount mismatch"):
        verify_payment(order.payment_track_id)

    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.FAILED
    transaction_log = PaymentTransaction.objects.get(
        order=order, event_type=PaymentTransaction.EventType.VERIFY
    )
    assert transaction_log.status == PaymentTransaction.Status.FAILED
    delay_mock.assert_not_called()


def test_verify_payment_order_id_mismatch_fails(mocker):
    order = _create_order_with_item(OrderFactory().user)
    order.payment_track_id = "track-111"
    order.save(update_fields=["payment_track_id"])

    mocker.patch(
        "payment.services.ZibalGateway.verify_payment",
        return_value={
            "result": 100,
            "amount": int(order.total_payable * 100),
            "orderId": "different-order",
        },
    )
    delay_mock = mocker.patch("payment.services.create_postex_shipment_task.delay")

    with pytest.raises(ValueError, match="OrderId mismatch"):
        verify_payment(order.payment_track_id)

    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.FAILED
    transaction_log = PaymentTransaction.objects.get(
        order=order, event_type=PaymentTransaction.EventType.VERIFY
    )
    assert transaction_log.status == PaymentTransaction.Status.FAILED
    delay_mock.assert_not_called()


def test_verify_payment_gateway_failure(mocker):
    order = _create_order_with_item(OrderFactory().user)
    order.payment_track_id = "track-222"
    order.save(update_fields=["payment_track_id"])

    mocker.patch(
        "payment.services.ZibalGateway.verify_payment",
        return_value={"result": 102, "message": "failed"},
    )
    delay_mock = mocker.patch("payment.services.create_postex_shipment_task.delay")

    with pytest.raises(ValueError, match="Payment verification failed"):
        verify_payment(order.payment_track_id)

    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.FAILED
    transaction_log = PaymentTransaction.objects.get(
        order=order, event_type=PaymentTransaction.EventType.VERIFY
    )
    assert transaction_log.status == PaymentTransaction.Status.FAILED
    delay_mock.assert_not_called()


def test_verify_payment_idempotent_when_already_verified(mocker):
    order = _create_order_with_item(OrderFactory().user)
    order.payment_track_id = "track-333"
    order.save(update_fields=["payment_track_id"])

    PaymentTransaction.objects.create(
        order=order,
        track_id=order.payment_track_id,
        event_type=PaymentTransaction.EventType.VERIFY,
        status=PaymentTransaction.Status.PROCESSED,
    )

    gateway_mock = mocker.patch("payment.services.ZibalGateway.verify_payment")

    message = verify_payment(order.payment_track_id)

    assert "already been successfully verified" in message
    gateway_mock.assert_not_called()
    assert (
        PaymentTransaction.objects.filter(
            track_id=order.payment_track_id,
            event_type=PaymentTransaction.EventType.VERIFY,
        ).count()
        == 1
    )
