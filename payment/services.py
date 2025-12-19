from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from orders.models import Order
from .gateways import ZibalGateway, ZibalGatewayError
from shipping.tasks import create_postex_shipment_task
from .models import PaymentTransaction


def process_payment(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    if order.payment_status == Order.PaymentStatus.SUCCESS:
        raise ValueError("This order has already been paid.")

    # Check stock just before payment
    for item in order.items.all():
        if item.product.stock < item.quantity:
            raise ValueError(f"Insufficient stock for product: {item.product.name}")

    # The callback URL is now the verify URL, as Zibal will redirect the user here.
    callback_url = request.build_absolute_uri(reverse("payment:verify"))
    gateway = ZibalGateway()

    try:
        # Assuming total_payable is in Toman, converting to Rials for Zibal
        amount_in_rials = int(order.total_payable * 10)
        response = gateway.create_payment_request(
            amount=amount_in_rials,
            order_id=order.order_id,
            callback_url=callback_url
        )

        order.payment_gateway = 'zibal'
        order.payment_track_id = response.get('trackId')
        order.save()

        PaymentTransaction.objects.create(
            order=order,
            track_id=order.payment_track_id,
            event_type=PaymentTransaction.EventType.INITIATE,
            status=PaymentTransaction.Status.PROCESSED,
            amount=amount_in_rials,
            result_code=str(response.get('result')),
            message="Payment request created successfully.",
            raw_payload={"order_id": str(order.order_id)},
            gateway_response=response,
        )
        payment_url = f"https://gateway.zibal.ir/start/{response.get('trackId')}"
        return payment_url
    except ZibalGatewayError as e:
        PaymentTransaction.objects.create(
            order=order,
            track_id=order.payment_track_id or "",
            event_type=PaymentTransaction.EventType.INITIATE,
            status=PaymentTransaction.Status.FAILED,
            amount=int(order.total_payable * 10),
            message=f"Failed to create payment request: {e}",
        )
        raise ValueError(f"Failed to create payment request: {e}")


def verify_payment(track_id, signature=None, ip_address=None, raw_payload=None):
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(payment_track_id=track_id)

            transaction_log = PaymentTransaction.objects.create(
                order=order,
                track_id=track_id,
                event_type=PaymentTransaction.EventType.VERIFY,
                status=PaymentTransaction.Status.RECEIVED,
                ip_address=ip_address,
                signature=signature or "",
                raw_payload=raw_payload or {},
            )

            # Idempotency Check: If already successful, do nothing more.
            if order.payment_status == Order.PaymentStatus.SUCCESS:
                transaction_log.status = PaymentTransaction.Status.SKIPPED
                transaction_log.message = "Order already marked as successful."
                transaction_log.save(update_fields=["status", "message", "updated_at"])
                return "This payment has already been successfully verified."

            gateway = ZibalGateway()
            response = gateway.verify_payment(track_id)
            result = response.get('result')

            transaction_log.gateway_response = response
            transaction_log.result_code = str(result)

            # A successful verification can have result 100 (new) or 201 (already verified by Zibal).
            if result in [100, 201]:
                # Integrity Check: Verify amount and orderId match the gateway's response.
                amount_from_gateway = response.get('amount')
                expected_amount = int(order.total_payable * 10)  # Assuming Toman to Rials conversion

                if amount_from_gateway != expected_amount:
                    order.payment_status = Order.PaymentStatus.FAILED
                    order.save(update_fields=["payment_status", "updated"])
                    transaction_log.status = PaymentTransaction.Status.FAILED
                    transaction_log.amount = amount_from_gateway
                    transaction_log.message = (
                        f"Amount mismatch. Expected {expected_amount}, but gateway reported {amount_from_gateway}."
                    )
                    transaction_log.save(
                        update_fields=[
                            "status",
                            "amount",
                            "message",
                            "gateway_response",
                            "result_code",
                            "updated_at",
                        ]
                    )
                    raise ValueError(transaction_log.message)

                order_id_from_gateway = response.get('orderId')
                if order_id_from_gateway != str(order.order_id):
                    order.payment_status = Order.PaymentStatus.FAILED
                    order.save(update_fields=["payment_status", "updated"])
                    transaction_log.status = PaymentTransaction.Status.FAILED
                    transaction_log.message = (
                        f"OrderId mismatch. Expected {order.order_id}, but gateway reported {order_id_from_gateway}."
                    )
                    transaction_log.save(
                        update_fields=[
                            "status",
                            "message",
                            "gateway_response",
                            "result_code",
                            "updated_at",
                        ]
                    )
                    raise ValueError(transaction_log.message)

                # All checks passed, update the order.
                order.payment_status = Order.PaymentStatus.SUCCESS
                order.payment_ref_id = response.get('refNumber', '')
                order.status = Order.Status.PAID
                order.save(update_fields=["payment_status", "payment_ref_id", "status", "updated"])

                transaction_log.status = PaymentTransaction.Status.PROCESSED
                transaction_log.amount = amount_from_gateway
                transaction_log.ref_id = order.payment_ref_id
                transaction_log.message = "Payment verified successfully."
                transaction_log.save(
                    update_fields=[
                        "status",
                        "amount",
                        "ref_id",
                        "message",
                        "gateway_response",
                        "result_code",
                        "updated_at",
                    ]
                )

                # Trigger asynchronous post-payment tasks.
                create_postex_shipment_task.delay(order.order_id)
                return "Payment verified successfully. Shipment creation is in progress."
            else:
                # Verification failed at the gateway.
                order.payment_status = Order.PaymentStatus.FAILED
                order.save(update_fields=["payment_status", "updated"])
                error_message = response.get('message', 'Unknown error.')
                transaction_log.status = PaymentTransaction.Status.FAILED
                transaction_log.message = f"Payment verification failed: {error_message} (Result code: {result})"
                transaction_log.save(
                    update_fields=[
                        "status",
                        "message",
                        "gateway_response",
                        "result_code",
                        "updated_at",
                    ]
                )
                raise ValueError(transaction_log.message)
    except Order.DoesNotExist:
        # This will be caught by the view and result in a 404.
        raise
