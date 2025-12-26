from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.utils import timezone

from orders.models import Order
from orders.tasks import cancel_pending_orders, send_order_confirmation_email
from orders.tests.factories import OrderFactory

pytestmark = pytest.mark.django_db


@patch("orders.tasks.send_mail", return_value=1)
def test_send_order_confirmation_email_success(mock_send_mail):
    order = OrderFactory()

    result = send_order_confirmation_email.run(order.order_id)

    assert result == 1
    mock_send_mail.assert_called_once()


@patch("orders.tasks.send_mail", side_effect=Exception("boom"))
def test_send_order_confirmation_email_retries_on_failure(mock_send_mail):
    order = OrderFactory()

    with patch.object(
        send_order_confirmation_email, "retry", side_effect=Retry()
    ) as mock_retry:
        with pytest.raises(Retry):
            send_order_confirmation_email.run(order.order_id)

    mock_send_mail.assert_called_once()
    mock_retry.assert_called_once()


def test_cancel_pending_orders_cancels_stale_orders():
    frozen_time = timezone.now()
    stale_order = OrderFactory(status=Order.Status.PENDING)
    fresh_order = OrderFactory(status=Order.Status.PENDING)

    stale_order.order_date = frozen_time - timedelta(minutes=30)
    stale_order.save(update_fields=["order_date"])
    fresh_order.order_date = frozen_time - timedelta(minutes=5)
    fresh_order.save(update_fields=["order_date"])

    with patch("orders.tasks.timezone.now", return_value=frozen_time):
        cancel_pending_orders()

    stale_order.refresh_from_db()
    fresh_order.refresh_from_db()

    assert stale_order.status == Order.Status.CANCELED
    assert fresh_order.status == Order.Status.PENDING
