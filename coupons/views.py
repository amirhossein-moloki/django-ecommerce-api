from logging import getLogger

from drf_spectacular.utils import extend_schema, OpenApiResponse, extend_schema_view
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from coupons.models import Coupon
from coupons.serializers import CouponSerializer
from . import services

logger = getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        operation_id="coupon_list",
        description="Only staff can list coupons.",
        tags=["Coupons"],
    ),
    retrieve=extend_schema(
        operation_id="coupon_retrieve",
        description="Only staff can retrieve a coupon.",
        tags=["Coupons"],
    ),
    create=extend_schema(
        operation_id="coupon_create",
        description="Only staff can create a coupon.",
        tags=["Coupons"],
    ),
    update=extend_schema(
        operation_id="coupon_update",
        description="Only staff can update a coupon. Prevent modification of the `code` field.",
        tags=["Coupons"],
        responses={
            200: OpenApiResponse(description="Coupon updated successfully."),
            400: OpenApiResponse(description="Coupon code cannot be modified or bad request."),
        },
    ),
    partial_update=extend_schema(
        operation_id="coupon_partial_update",
        description="Only staff can partially update a coupon. Prevent modification of the `code` field.",
        tags=["Coupons"],
        responses={
            200: OpenApiResponse(description="Coupon updated successfully."),
            400: OpenApiResponse(description="Coupon code cannot be modified or bad request."),
        },
    ),
    destroy=extend_schema(
        operation_id="coupon_destroy",
        description="Only staff can delete a coupon. Mark the coupon as inactive instead.",
        tags=["Coupons"],
        responses={
            200: OpenApiResponse(description="Coupon has been marked as inactive."),
        },
    ),
    apply=extend_schema(
        operation_id="coupon_apply",
        description="Apply a coupon by its code.",
        tags=["Coupons"],
        responses={
            200: OpenApiResponse(description="Coupon applied successfully."),
            400: OpenApiResponse(description="Coupon code is required or coupon is not valid at this time."),
            404: OpenApiResponse(description="Invalid or inactive coupon code."),
        },
    ),
)
class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]

    def update(self, request, *args, **kwargs):
        """
        Prevent modification of the `code` field.
        """
        try:
            instance = self.get_object()
            services.update_coupon(instance, request.data)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating coupon: {e}", exc_info=True)
            raise

    def destroy(self, request, *args, **kwargs):
        """
        Mark the coupon as inactive instead of deleting it.
        """
        try:
            instance = self.get_object()
            services.deactivate_coupon(instance)
            return Response(
                {"detail": "Coupon has been marked as inactive."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error deactivating coupon: {e}", exc_info=True)
            raise

    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    @action(
        detail=False,
        methods=['post'],
        url_path='apply-coupon',
        url_name='apply-coupon',
        permission_classes=[permissions.AllowAny]
    )
    def apply(self, request):
        """
        Apply a coupon by its code.
        """
        try:
            code = request.data.get('code')
            if not code:
                return Response(
                    {"detail": "Coupon code is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            coupon = services.apply_coupon(request, code)
            return Response(
                {"detail": "Coupon applied successfully.", "discount": coupon.discount},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error applying coupon: {e}", exc_info=True)
            raise
