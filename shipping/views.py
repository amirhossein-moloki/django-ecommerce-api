from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404
from orders.models import Order
from .providers import PostexShippingProvider, ShippingProviderError
from ecommerce_api.core.api_standard_response import ApiResponse
import logging

logger = logging.getLogger(__name__)


class CityListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            provider = PostexShippingProvider()
            response = provider.get_cities()
            return ApiResponse.success(data=response, status_code=status.HTTP_200_OK)
        except ShippingProviderError as e:
            logger.error(f"Failed to get city list from Postex: {e}")
            return ApiResponse.error(
                message=f"Failed to get city list: {e}",
                status_code=e.status_code or status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("An unexpected error occurred while fetching city list.")
            return ApiResponse.error(
                message="An unexpected error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CalculateShippingCostAPIView(APIView):
    def post(self, request, *args, **kwargs):
        order_id = request.data.get("order_id")
        if not order_id:
            return ApiResponse.error(
                message="Order ID is required", status_code=status.HTTP_400_BAD_REQUEST
            )

        order = get_object_or_404(Order, order_id=order_id)

        if not order.address:
            return ApiResponse.error(
                message="Order address is not set",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            provider = PostexShippingProvider()
            response = provider.get_shipping_quote(order)

            quotes = response.get("data", {}).get("quotes", [])
            if not quotes:
                return ApiResponse.error(
                    message="No shipping options available for the destination.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # Assuming the first quote is the desired one
            shipping_cost = quotes[0].get("price", 0)

            order.shipping_cost = shipping_cost
            order.save(update_fields=["shipping_cost"])

            return ApiResponse.success(
                data={"shipping_cost": shipping_cost}, status_code=status.HTTP_200_OK
            )

        except ShippingProviderError as e:
            logger.error(f"Failed to get shipping cost for order {order_id}: {e}")
            return ApiResponse.error(
                message=f"Failed to get shipping cost: {e}",
                status_code=e.status_code or status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception:
            logger.exception(
                f"An unexpected error occurred while calculating shipping cost for order {order_id}."
            )
            return ApiResponse.error(
                message="An unexpected error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
