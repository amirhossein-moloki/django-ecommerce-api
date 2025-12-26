from celery import shared_task
from .providers import PostexShippingProvider, ShippingProviderError
from orders.models import Order
import logging

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(ShippingProviderError,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def create_postex_shipment_task(order_id):
    try:
        order = Order.objects.get(order_id=order_id, status=Order.Status.PAID)
        shipping_provider = PostexShippingProvider()

        logger.info(f"Attempting to create shipment for order: {order_id}")
        shipping_response = shipping_provider.create_shipment(order)

        orders_data = shipping_response.get("data", {}).get("orders", [])
        if orders_data and orders_data[0].get("parcels"):
            parcel_data = orders_data[0]["parcels"][0]

            order.shipping_provider = "postex"
            order.postex_parcel_no = parcel_data.get("parcel_no")
            order.postex_order_no = orders_data[0].get("order_no")
            order.status = Order.Status.PROCESSING
            order.save(
                update_fields=[
                    "shipping_provider",
                    "postex_parcel_no",
                    "postex_order_no",
                    "status",
                ]
            )

            logger.info(
                f"Successfully created shipment for order: {order_id} with parcel_no: {order.postex_parcel_no}"
            )
        else:
            logger.error(
                f"Postex response for order {order_id} was successful but lacked expected data: {shipping_response}"
            )
            # Potentially raise an error to trigger a retry if the data format is unexpectedly wrong
            raise ShippingProviderError(
                "Invalid data in Postex response", status_code=500
            )

    except Order.DoesNotExist:
        logger.warning(
            f"Order with ID {order_id} not found or not in PAID status for shipment creation."
        )

    except ShippingProviderError as e:
        logger.error(f"A shipping provider error occurred for order {order_id}: {e}")
        # The task will be retried automatically due to autoretry_for
        raise

    except Exception as e:
        logger.exception(
            f"An unexpected error occurred in create_postex_shipment_task for order {order_id}."
        )
        # Depending on the policy, you might want to retry this too.
        # For now, we let it fail.
