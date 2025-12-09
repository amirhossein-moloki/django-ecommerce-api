from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import send_mail
from django.utils import timezone

from .models import Order

logger = get_task_logger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 5})
def send_order_confirmation_email(self, order_pk):
    """
    Task to send an e-mail notification when an order is
    successfully created. Retries on failure.
    """
    try:
        order = Order.objects.get(pk=order_pk)
        subject = f'Order nr. {order.order_id}'
        message = (
            f'Dear {order.user.username},\n\n'
            f'You have successfully placed an order.'
            f'Your order ID is {order.order_id}.'
        )
        mail_sent = send_mail(
            subject, message, 'admin@eCommerce.com', [order.user.email]
        )
        return mail_sent
    except Exception as e:
        logger.error(f"Error sending confirmation email for order {order_pk}: {e}")
        raise self.retry(exc=e)


@shared_task
def cancel_pending_orders():
    """
    Task to cancel pending orders that have not been paid for within a certain timeframe.
    """
    time_threshold = timezone.now() - timedelta(minutes=20)
    pending_orders = Order.objects.filter(status=Order.Status.PENDING, order_date__lte=time_threshold)

    for order in pending_orders:
        order.status = Order.Status.CANCELED
        order.save()
        logger.info(f"Canceled pending order {order.order_id}")
