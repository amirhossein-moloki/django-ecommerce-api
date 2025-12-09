from logging import getLogger

from drf_spectacular.utils import extend_schema, OpenApiResponse, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ecommerce_api.core.api_standard_response import ApiResponse
from orders.models import Order
from . import services
import hmac
from .tasks import process_successful_payment
from ecommerce_api.core.utils import get_client_ip
from django.conf import settings
from rest_framework.permissions import AllowAny

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
    post=extend_schema(
        operation_id="payment_webhook",
        description="Webhook for Zibal payment gateway to send payment status updates.",
        tags=["Payments"],
        request=None,
        responses={
            200: OpenApiResponse(description="Webhook received and accepted for processing."),
            400: OpenApiResponse(description="Invalid webhook request (e.g., missing headers, invalid IP).")
        },
    )
)
class PaymentWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Security: Validate the webhook signature
        gateway_signature = request.headers.get('X-Gateway-Signature')
        if not gateway_signature:
            logger.warning("Webhook request missing X-Gateway-Signature header.")
            return ApiResponse.error(message="Invalid signature.", status_code=status.HTTP_403_FORBIDDEN)

        computed_signature = hmac.new(
            settings.ZIBAL_WEBHOOK_SECRET.encode('utf-8'),
            request.body,
            'sha256'
        ).hexdigest()

        if not hmac.compare_digest(gateway_signature, computed_signature):
            logger.warning("Invalid webhook signature.")
            return ApiResponse.error(message="Invalid signature.", status_code=status.HTTP_403_FORBIDDEN)

        # Security: Check the source IP (optional but recommended)
        client_ip = get_client_ip(request)
        if client_ip not in settings.ZIBAL_ALLOWED_IPS:
            logger.warning(f"Webhook request from unauthorized IP: {client_ip}")
            return ApiResponse.error(message="Invalid source IP.", status_code=status.HTTP_403_FORBIDDEN)

        data = request.data
        track_id = data.get('trackId')
        success = data.get('success')

        if not track_id:
            return ApiResponse.error(message="trackId is required.", status_code=status.HTTP_400_BAD_REQUEST)

        # Idempotency Check
        try:
            order = Order.objects.get(payment_track_id=track_id)
            if order.payment_status == Order.PaymentStatus.SUCCESS:
                logger.info(f"Webhook for track_id {track_id} already processed successfully.")
                return ApiResponse.success(message="Webhook already processed.", status_code=status.HTTP_200_OK)
        except Order.DoesNotExist:
            # This can happen if the webhook arrives before the order is saved.
            # The Celery task will handle this gracefully.
            pass

        # Asynchronously process the payment to avoid blocking the gateway
        process_successful_payment.delay(track_id, success)

        return ApiResponse.success(message="Webhook received.", status_code=status.HTTP_200_OK)


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
