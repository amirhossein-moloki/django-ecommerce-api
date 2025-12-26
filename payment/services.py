from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from orders.models import Order
from .gateways import ZibalGateway, ZibalGatewayError
from shipping.tasks import create_postex_shipment_task
from .models import PaymentTransaction


def process_payment(request, order_id):
    try:
        with transaction.atomic():
            # Lock the order to prevent race conditions during payment processing.
            order = Order.objects.select_for_update().get(
                order_id=order_id, user=request.user
            )

            if order.payment_status == Order.PaymentStatus.SUCCESS:
                raise ValueError("This order has already been paid.")

            # Atomically update item prices and check stock before any calculations.
            # Lock the related products to prevent overselling race conditions.
            for item in order.items.select_related(
                "variant__product"
            ).select_for_update(of=("self", "variant")):
                if item.variant.stock < item.quantity:
                    raise ValueError(
                        f"Insufficient stock for product: {item.variant.product.name}"
                    )
                # Snapshot the current price, in case it has changed since the order was created.
                if item.price != item.variant.price:
                    item.price = item.variant.price
                    item.save(update_fields=["price"])

            # Re-validate coupon with the most up-to-date prices.
            if order.coupon:
                if not order.coupon.is_valid():
                    raise ValueError(
                        f"The coupon '{order.coupon.code}' is no longer valid."
                    )

                if order.coupon.usage_count >= order.coupon.max_usage:
                    raise ValueError(
                        f"The coupon '{order.coupon.code}' has reached its usage limit."
                    )

                subtotal = order.get_total_cost_before_discount()
                if subtotal < order.coupon.min_purchase_amount:
                    raise ValueError(
                        f"Order subtotal does not meet the minimum purchase amount of "
                        f"{order.coupon.min_purchase_amount} for coupon '{order.coupon.code}'."
                    )

            # Recalculate all order totals based on the latest data.
            order.calculate_total_payable()
            order.save()

            # The callback URL is now the verify URL, as Zibal will redirect the user here.
            callback_url = request.build_absolute_uri(reverse("payment:verify"))
            gateway = ZibalGateway()

            # Assuming total_payable is in Toman, converting to Rials for Zibal
            amount_in_rials = int(order.total_payable * 100)
            response = gateway.create_payment_request(
                amount=amount_in_rials,
                order_id=str(order.order_id),
                callback_url=callback_url,
            )

            order.payment_gateway = "zibal"
            order.payment_track_id = response.get("trackId")
            order.save(update_fields=["payment_gateway", "payment_track_id", "updated"])

            PaymentTransaction.objects.create(
                order=order,
                track_id=order.payment_track_id,
                event_type=PaymentTransaction.EventType.INITIATE,
                status=PaymentTransaction.Status.PROCESSED,
                amount=amount_in_rials,
                result_code=str(response.get("result")),
                message="Payment request created successfully.",
                raw_payload={"order_id": str(order.order_id)},
                gateway_response=response,
            )
            payment_url = f"https://gateway.zibal.ir/start/{response.get('trackId')}"
            return payment_url

    except Order.DoesNotExist:
        raise ValueError("Order not found or you do not have permission to access it.")
    except (ZibalGatewayError, ValueError) as e:
        # Try to log the failure, but don't fail if the order can't be found.
        order = Order.objects.filter(order_id=order_id, user=request.user).first()
        if order:
            PaymentTransaction.objects.create(
                order=order,
                track_id=order.payment_track_id or "",
                event_type=PaymentTransaction.EventType.INITIATE,
                status=PaymentTransaction.Status.FAILED,
                amount=int(order.total_payable * 100) if order.total_payable else 0,
                message=f"Failed to create payment request: {e}",
            )
        # Re-raise the original exception to be handled by the view.
        raise e


def verify_payment(track_id, signature=None, ip_address=None, raw_payload=None):
    # Idempotency Check: Prevent re-processing successful verifications.
    if PaymentTransaction.objects.filter(
        track_id=track_id,
        event_type=PaymentTransaction.EventType.VERIFY,
        status=PaymentTransaction.Status.PROCESSED,
    ).exists():
        return "This payment has already been successfully verified."

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
            result = response.get("result")

            transaction_log.gateway_response = response
            transaction_log.result_code = str(result)

            # A successful verification can have result 100 (new) or 201 (already verified by Zibal).
            if result in [100, 201]:
                # Integrity Check: Verify amount and orderId match the gateway's response.
                amount_from_gateway = response.get("amount")
                expected_amount = int(
                    order.total_payable * 100
                )  # Assuming Toman to Rials conversion

                if amount_from_gateway != expected_amount:
                    order.payment_status = Order.PaymentStatus.FAILED
                    order.save(update_fields=["payment_status", "updated"])
                    transaction_log.status = PaymentTransaction.Status.FAILED
                    transaction_log.amount = amount_from_gateway
                    transaction_log.message = f"Amount mismatch. Expected {expected_amount}, but gateway reported {amount_from_gateway}."
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

                order_id_from_gateway = response.get("orderId")
                if order_id_from_gateway != str(order.order_id):
                    order.payment_status = Order.PaymentStatus.FAILED
                    order.save(update_fields=["payment_status", "updated"])
                    transaction_log.status = PaymentTransaction.Status.FAILED
                    transaction_log.message = f"OrderId mismatch. Expected {order.order_id}, but gateway reported {order_id_from_gateway}."
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
                order.payment_ref_id = response.get("refNumber", "")
                order.status = Order.Status.PAID
                order.save(
                    update_fields=[
                        "payment_status",
                        "payment_ref_id",
                        "status",
                        "updated",
                    ]
                )

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
                return (
                    "Payment verified successfully. Shipment creation is in progress."
                )
            else:
                # Verification failed at the gateway.
                order.payment_status = Order.PaymentStatus.FAILED
                order.save(update_fields=["payment_status", "updated"])
                error_message = response.get("message", "Unknown error.")
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
