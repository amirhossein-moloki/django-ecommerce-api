import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone

from .tasks import send_order_confirmation_email, cancel_pending_orders
from .factories import OrderFactory
from .models import Order

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(transaction=True)
class TestOrderTasks:
    @patch('orders.tasks.send_mail')
    def test_send_order_confirmation_email_success(self, mock_send_mail):
        """
        Test that the confirmation email task correctly calls send_mail on success.
        """
        order = OrderFactory()
        send_order_confirmation_email(order.pk)

        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        assert f'Order nr. {order.order_id}' in args[0]
        assert f'Dear {order.user.username}' in args[1]
        assert kwargs['recipient_list'] == [order.user.email]

    @patch('orders.tasks.send_order_confirmation_email.retry')
    @patch('orders.tasks.send_mail', side_effect=Exception('SMTP Error'))
    def test_send_order_confirmation_email_retry(self, mock_send_mail, mock_retry):
        """
        Test that the confirmation email task retries on failure.
        """
        order = OrderFactory()
        mock_task = MagicMock()
        send_order_confirmation_email.__self__ = mock_task

        with pytest.raises(Exception):
            send_order_confirmation_email(order.pk)

        mock_send_mail.assert_called_once()
        mock_task.retry.assert_called_once()


    def test_cancel_pending_orders(self):
        """
        Test that old pending orders are canceled, while recent or non-pending
        orders are not.
        """
        # 1. An old pending order that should be canceled
        old_pending_order = OrderFactory(status=Order.Status.PENDING)
        old_pending_order.order_date = timezone.now() - timedelta(minutes=30)
        old_pending_order.save()

        # 2. A recent pending order that should NOT be canceled
        OrderFactory(status=Order.Status.PENDING)

        # 3. An old paid order that should NOT be canceled
        old_paid_order = OrderFactory(status=Order.Status.PAID)
        old_paid_order.order_date = timezone.now() - timedelta(minutes=30)
        old_paid_order.save()

        # Run the task
        cancel_pending_orders()

        # Verify the statuses
        old_pending_order.refresh_from_db()
        assert old_pending_order.status == Order.Status.CANCELED

        assert Order.objects.filter(status=Order.Status.PENDING).count() == 1

        old_paid_order.refresh_from_db()
        assert old_paid_order.status == Order.Status.PAID
