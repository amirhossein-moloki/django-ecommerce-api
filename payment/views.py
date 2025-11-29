from logging import getLogger

from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiResponse, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ecommerce_api.core.api_standard_response import ApiResponse
from orders.models import Order
from . import services
from shipping.tasks import create_postex_shipment_task

logger = getLogger(__name__)


@extend_schema_view(
    post=extend_schema(
        operation_id="payment_process",
        description="Create a Zibal payment request for an order. Expects an order_id in request data.",
        tags=["Payments"],
        responses={
            201: OpenApiResponse(description="Zibal payment URL created successfully."),
            400: OpenApiResponse(description="Order ID is missing or invalid request data.")
        },
    )
)
class PaymentProcessAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        order_id = kwargs.get("order_id")
        if not order_id:
            return ApiResponse.error(
                message="Order ID is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        try:
            payment_url = services.process_payment(request, order_id)
            return ApiResponse.success(
                data={"payment_url": payment_url},
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return ApiResponse.error(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


@extend_schema_view(
    get=extend_schema(
        operation_id="payment_verify",
        description="Verify a Zibal payment.",
        tags=["Payments"],
        responses={
            200: OpenApiResponse(description="Payment verified successfully."),
            400: OpenApiResponse(description="Invalid payment verification request.")
        },
    )
)
class PaymentVerifyAPIView(APIView):
    def get(self, request, *args, **kwargs):
        track_id = request.query_params.get('trackId')
        if not track_id:
            return ApiResponse.error(
                message="trackId is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        try:
            message = services.verify_payment(track_id)
            return ApiResponse.success(
                message=message,
                status_code=status.HTTP_200_OK
            )
        except Order.DoesNotExist:
            return ApiResponse.error(
                message="Order not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return ApiResponse.error(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
