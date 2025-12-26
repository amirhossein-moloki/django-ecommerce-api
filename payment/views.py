import hashlib
import hmac
from logging import getLogger
from urllib.parse import urlencode

from drf_spectacular.utils import extend_schema, OpenApiResponse, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from django.conf import settings

from ecommerce_api.core.api_standard_response import ApiResponse
from ecommerce_api.core.utils import get_client_ip
from orders.models import Order
from . import services
from .models import PaymentTransaction

logger = getLogger(__name__)


@extend_schema_view(
    post=extend_schema(
        operation_id="payment_process",
        description="Create a Zibal payment request for an order. Expects an order_id in request data.",
        tags=["Payments"],
        responses={
            201: OpenApiResponse(description="Zibal payment URL created successfully."),
            400: OpenApiResponse(
                description="Order ID is missing or invalid request data."
            ),
        },
    )
)
class PaymentProcessAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        order_id = kwargs.get("order_id")
        if not order_id:
            return ApiResponse.error(
                message="Order ID is required.", status_code=status.HTTP_400_BAD_REQUEST
            )
        try:
            payment_url = services.process_payment(request, order_id)
            return ApiResponse.success(
                data={"payment_url": payment_url}, status_code=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return ApiResponse.error(
                message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )


from .gateways import ZibalGatewayError


@extend_schema_view(
    get=extend_schema(
        operation_id="payment_callback_and_verify",
        description="Handles the callback from Zibal after a payment attempt and performs server-side verification.",
        tags=["Payments"],
        responses={
            200: OpenApiResponse(description="Payment verified successfully."),
            400: OpenApiResponse(
                description="Invalid callback request or verification failed."
            ),
            404: OpenApiResponse(description="Order not found for the given trackId."),
        },
    )
)
class PaymentVerifyAPIView(APIView):
    """
    This view handles the user's return from the Zibal payment gateway.
    It receives the trackId and success status from Zibal via query parameters.
    It then immediately calls the verification service to confirm the payment
    with Zibal's server, ensuring a secure verification process.
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        track_id = request.query_params.get("trackId")
        success = request.query_params.get("success")
        success_value = success if success is not None else ""
        raw_payload = {"trackId": track_id, "success": success_value}
        signature = request.headers.get("X-Zibal-Signature", "")
        client_ip = get_client_ip(request)
        allowed_ips = getattr(settings, "ZIBAL_ALLOWED_IPS", [])

        if not track_id:
            logger.error("Zibal callback received without trackId.")
            return ApiResponse.error(
                message="Required parameter 'trackId' is missing.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if client_ip and allowed_ips and client_ip not in allowed_ips:
            PaymentTransaction.objects.create(
                order=Order.objects.filter(payment_track_id=track_id).first(),
                track_id=track_id,
                event_type=PaymentTransaction.EventType.VERIFY,
                status=PaymentTransaction.Status.REJECTED,
                ip_address=client_ip,
                signature=signature,
                raw_payload=raw_payload,
                message="Callback rejected due to IP allowlist.",
            )
            return ApiResponse.error(
                message="Request not allowed from this IP.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        expected_signature = hmac.new(
            getattr(settings, "ZIBAL_WEBHOOK_SECRET", "").encode("utf-8"),
            urlencode(sorted(raw_payload.items())).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not signature or not hmac.compare_digest(signature, expected_signature):
            PaymentTransaction.objects.create(
                order=Order.objects.filter(payment_track_id=track_id).first(),
                track_id=track_id,
                event_type=PaymentTransaction.EventType.VERIFY,
                status=PaymentTransaction.Status.REJECTED,
                ip_address=client_ip,
                signature=signature,
                raw_payload=raw_payload,
                message="Invalid or missing signature on callback.",
            )
            return ApiResponse.error(
                message="Invalid signature.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if success_value != "1":
            logger.warning(
                f"Zibal callback for trackId {track_id} indicates a failed or canceled payment."
            )
            PaymentTransaction.objects.create(
                order=Order.objects.filter(payment_track_id=track_id).first(),
                track_id=track_id,
                event_type=PaymentTransaction.EventType.VERIFY,
                status=PaymentTransaction.Status.FAILED,
                ip_address=client_ip,
                signature=signature,
                raw_payload=raw_payload,
                message="Gateway callback indicated failure or cancellation.",
            )
            return ApiResponse.error(
                message="Payment was not successful or was canceled by the user.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            message = services.verify_payment(
                track_id,
                signature=signature,
                ip_address=client_ip,
                raw_payload=raw_payload,
            )
            # In a real frontend application, you would redirect the user to a success page.
            # For an API, returning a success message is appropriate.
            return ApiResponse.success(message=message, status_code=status.HTTP_200_OK)
        except Order.DoesNotExist:
            logger.error(f"Verification failed: No order found for trackId {track_id}.")
            PaymentTransaction.objects.create(
                order=None,
                track_id=track_id,
                event_type=PaymentTransaction.EventType.VERIFY,
                status=PaymentTransaction.Status.REJECTED,
                ip_address=client_ip,
                signature=signature,
                raw_payload=raw_payload,
                message="Order not found for provided trackId.",
            )
            return ApiResponse.error(
                message="Order not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        except (ValueError, ZibalGatewayError) as e:
            logger.error(f"Payment verification error for trackId {track_id}: {e}")
            # In a real frontend application, you would redirect the user to a failure page.
            return ApiResponse.error(
                message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )
