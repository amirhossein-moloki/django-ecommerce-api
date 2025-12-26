from logging import getLogger

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from ecommerce_api.core.api_standard_response import ApiResponse
from .serializers import CartSerializer, AddToCartSerializer
from . import services
from shop.models import ProductVariant

logger = getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        operation_id="cart_retrieve_list",
        description="Retrieve the cart details, including all items and the total price.",
        tags=["Cart"],
        responses={
            200: OpenApiResponse(
                response=CartSerializer,
                description="Cart details retrieved successfully.",
            ),
        },
    ),
    add_to_cart=extend_schema(
        operation_id="cart_add_variant",
        description="Add a product variant to the cart or update its quantity.",
        tags=["Cart"],
        request=AddToCartSerializer,
        responses={
            200: OpenApiResponse(description="Product variant added/updated in cart."),
            400: OpenApiResponse(description="Invalid quantity provided."),
            404: OpenApiResponse(description="Product variant not found."),
        },
    ),
    remove_from_cart=extend_schema(
        operation_id="cart_remove_variant",
        description="Remove a product variant from the cart.",
        tags=["Cart"],
        responses={
            200: OpenApiResponse(description="Product variant removed from cart."),
            404: OpenApiResponse(description="Product variant not found."),
        },
    ),
)
class CartViewSet(viewsets.ViewSet):
    """
    A viewset for viewing and editing cart items.
    """

    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    queryset = None
    lookup_field = "variant_id"
    lookup_url_kwarg = "variant_id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return None  # For schema generation

    @extend_schema(
        operation_id="cart_get_details",
        description="Get the current cart contents with total price.",
        tags=["Cart"],
        responses={
            200: OpenApiResponse(
                response=CartSerializer,
                description="Cart details retrieved successfully.",
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        """
        Retrieve the cart details, including all items and the total price.

        Args:
            request: The HTTP request object.

        Returns:
            Response: A JSON response containing the cart details and total price.
        """
        cart_data = services.get_cart_data(request)
        serializer = CartSerializer(cart_data, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="add")
    def add_to_cart(self, request, variant_id=None):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            services.add_to_cart(
                request,
                variant_id,
                data.get("quantity", 1),
                data.get("override", False),
                allow_insufficient_stock=True,
            )
            return Response(
                {"message": "Product added/updated in cart"},
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            logger.warning(f"Add to cart validation error: {e.detail}")
            return ApiResponse.error(
                message=str(e.detail), status_code=status.HTTP_400_BAD_REQUEST
            )
        except ProductVariant.DoesNotExist:
            logger.warning(f"ProductVariant with id {variant_id} not found.")
            return ApiResponse.error(
                message="Product not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Unexpected error adding product to cart: {e}", exc_info=True)
            return ApiResponse.error(
                message="An unexpected error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["delete"], url_path="remove")
    def remove_from_cart(self, request, variant_id=None):
        """
        Remove a product from the cart.

        Args:
            request: The HTTP request object.
            variant_id: The ID of the product variant to remove.

        Returns:
            Response: A JSON response indicating success or failure.
        """
        try:
            services.remove_from_cart(request, variant_id)
            return Response(
                {"message": "Product removed from cart"}, status=status.HTTP_200_OK
            )
        except ProductVariant.DoesNotExist:
            logger.warning(
                f"ProductVariant with id {variant_id} not found for removal."
            )
            return ApiResponse.error(
                message="Product not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(
                f"Unexpected error removing product {variant_id} from cart: {e}",
                exc_info=True,
            )
            return ApiResponse.error(
                message="An unexpected error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["delete"], url_path="clear")
    @extend_schema(
        operation_id="cart_clear",
        description="Clear all items from the cart.",
        tags=["Cart"],
        responses={
            204: OpenApiResponse(description="Cart cleared successfully."),
        },
    )
    def clear_cart(self, request):
        """
        Clear all items from the cart.

        Args:
            request: The HTTP request object.

        Returns:
            Response: An empty response with a 204 status code.
        """
        cart = services.get_cart_data(request)
        if cart:
            services.clear_cart(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
