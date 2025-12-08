from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import status
from ecommerce_api.core.api_standard_response import ApiResponse
from orders.models import Order
from .gateways import ZibalGateway
from shipping.tasks import create_postex_shipment_task


def process_payment(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    if order.payment_status == Order.PaymentStatus.SUCCESS:
        raise ValueError("This order has already been paid.")

    for item in order.items.all():
        if item.product.stock < item.quantity:
            raise ValueError(f"Insufficient stock for product: {item.product.name}")

    # Use the secure webhook for server-to-server confirmation
    callback_url = request.build_absolute_uri(reverse("payment:webhook"))
    gateway = ZibalGateway()
    response = gateway.create_payment_request(
        amount=int(order.total_payable * 10),
        order_id=order.order_id,
        callback_url=callback_url
    )

    if response.get('result') == 100:
        order.payment_gateway = 'zibal'
        order.payment_track_id = response.get('trackId')
        order.save()
        payment_url = f"https://gateway.zibal.ir/start/{response.get('trackId')}"
        return payment_url
    else:
        raise ValueError("Failed to create payment request.")


def verify_payment(track_id):
    try:
        order = Order.objects.get(payment_track_id=track_id)
    except Order.DoesNotExist:
        raise Order.DoesNotExist

    gateway = ZibalGateway()
    response = gateway.verify_payment(track_id)

    if response.get('result') == 100:
        order.payment_status = Order.PaymentStatus.SUCCESS
        order.payment_ref_id = response.get('refNumber', '')
        order.status = Order.Status.PAID
        order.save()
        create_postex_shipment_task.delay(order.order_id)
        return "Payment verified. Shipment creation is in progress."
    else:
        order.payment_status = Order.PaymentStatus.FAILED
        order.save()
        raise ValueError("Payment verification failed.")
