import hashlib
import hmac
from urllib.parse import urlencode

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.tests.factories import UserFactory
from orders.tests.factories import OrderFactory
from payment.models import PaymentTransaction


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def _signature_for(payload):
    return hmac.new(
        settings.ZIBAL_WEBHOOK_SECRET.encode("utf-8"),
        urlencode(sorted(payload.items())).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def test_process_payment_requires_owner(api_client, mocker):
    owner = UserFactory()
    other_user = UserFactory()
    order = OrderFactory(user=owner)
    url = reverse("payment:process", kwargs={"order_id": order.order_id})

    api_client.force_authenticate(user=other_user)
    mocker.patch(
        "payment.views.services.process_payment",
        side_effect=ValueError("Order not found or you do not have permission to access it."),
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_process_payment_missing_order_id(api_client):
    api_client.force_authenticate(user=UserFactory())
    url = "/payment/process/"

    response = api_client.post(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_process_payment_invalid_order_id(api_client, mocker):
    user = UserFactory()
    url = reverse("payment:process", kwargs={"order_id": OrderFactory().order_id})
    api_client.force_authenticate(user=user)

    mocker.patch(
        "payment.views.services.process_payment",
        side_effect=ValueError("Order not found or you do not have permission to access it."),
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Order not found" in response.data["message"]


def test_process_payment_handles_value_error(api_client, mocker):
    user = UserFactory()
    order = OrderFactory(user=user)
    url = reverse("payment:process", kwargs={"order_id": order.order_id})
    api_client.force_authenticate(user=user)

    mocker.patch(
        "payment.views.services.process_payment",
        side_effect=ValueError("bad order"),
    )

    response = api_client.post(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "bad order" in response.data["message"]


def test_verify_payment_missing_track_id(api_client):
    url = reverse("payment:verify")
    response = api_client.get(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_verify_payment_success_not_one(api_client):
    order = OrderFactory()
    order.payment_track_id = "track-1"
    order.save(update_fields=["payment_track_id"])
    url = reverse("payment:verify")
    payload = {"trackId": order.payment_track_id, "success": "0"}
    signature = _signature_for(payload)

    response = api_client.get(url, payload, HTTP_X_ZIBAL_SIGNATURE=signature)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert PaymentTransaction.objects.filter(track_id=order.payment_track_id).exists()


def test_verify_payment_invalid_signature(api_client):
    order = OrderFactory()
    order.payment_track_id = "track-2"
    order.save(update_fields=["payment_track_id"])
    url = reverse("payment:verify")
    payload = {"trackId": order.payment_track_id, "success": "1"}

    response = api_client.get(url, payload, HTTP_X_ZIBAL_SIGNATURE="invalid")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_verify_payment_rejects_ip(api_client, settings):
    settings.ZIBAL_ALLOWED_IPS = ["10.0.0.1"]
    order = OrderFactory()
    order.payment_track_id = "track-3"
    order.save(update_fields=["payment_track_id"])
    url = reverse("payment:verify")
    payload = {"trackId": order.payment_track_id, "success": "1"}
    signature = _signature_for(payload)

    response = api_client.get(
        url,
        payload,
        HTTP_X_ZIBAL_SIGNATURE=signature,
        REMOTE_ADDR="127.0.0.1",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_verify_payment_success_triggers_service_once(api_client, mocker):
    order = OrderFactory()
    order.payment_track_id = "track-4"
    order.save(update_fields=["payment_track_id"])
    url = reverse("payment:verify")
    payload = {"trackId": order.payment_track_id, "success": "1"}
    signature = _signature_for(payload)
    verify_mock = mocker.patch("payment.views.services.verify_payment", return_value="ok")

    response = api_client.get(url, payload, HTTP_X_ZIBAL_SIGNATURE=signature)

    assert response.status_code == status.HTTP_200_OK
    verify_mock.assert_called_once()


def test_verify_payment_idempotent_api_callback(api_client, mocker):
    order = OrderFactory()
    order.payment_track_id = "track-5"
    order.save(update_fields=["payment_track_id"])
    url = reverse("payment:verify")
    payload = {"trackId": order.payment_track_id, "success": "1"}
    signature = _signature_for(payload)
    mocker.patch(
        "payment.services.ZibalGateway.verify_payment",
        return_value={
            "result": 100,
            "amount": int(order.total_payable * 100),
            "orderId": str(order.order_id),
            "refNumber": "ref-1",
        },
    )
    delay_mock = mocker.patch("payment.services.create_postex_shipment_task.delay")

    first = api_client.get(url, payload, HTTP_X_ZIBAL_SIGNATURE=signature)
    second = api_client.get(url, payload, HTTP_X_ZIBAL_SIGNATURE=signature)

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert (
        PaymentTransaction.objects.filter(
            track_id=order.payment_track_id,
            event_type=PaymentTransaction.EventType.VERIFY,
            status=PaymentTransaction.Status.PROCESSED,
        ).count()
        == 1
    )
    delay_mock.assert_called_once_with(order.order_id)
