from logging import getLogger

from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
    OpenApiExample,
)
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import permissions, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from ecommerce_api.core.mixins import PaginationMixin
from ecommerce_api.core.permissions import IsOwnerOrStaff
from shop.filters import ProductFilter, InStockFilterBackend, ProductSearchFilterBackend
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer, ProductDetailSerializer
from .serializers import ReviewSerializer
from . import services

logger = getLogger(__name__)


@extend_schema_view(
    retrieve=extend_schema(
        operation_id="review_retrieve",
        description="Retrieve a specific review by ID.",
        tags=["Reviews"],
        responses={
            200: OpenApiResponse(description="Review retrieved successfully."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Review not found."),
        },
    ),
    list=extend_schema(
        operation_id="review_list",
        description="List all reviews for a product.",
        tags=["Reviews"],
        responses={200: OpenApiResponse(description="Reviews retrieved successfully.")},
    ),
    create=extend_schema(
        operation_id="review_create",
        description="Create a new review for a product. Requires authentication.",
        tags=["Reviews"],
        responses={
            201: OpenApiResponse(description="Review created successfully."),
            400: OpenApiResponse(description="Invalid input data."),
            401: OpenApiResponse(description="Authentication required."),
        },
    ),
    update=extend_schema(
        operation_id="review_update",
        description="Update an existing review. Only the review owner can update.",
        tags=["Reviews"],
        responses={
            200: OpenApiResponse(description="Review updated successfully."),
            400: OpenApiResponse(description="Invalid input data."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Review not found."),
        },
    ),
    partial_update=extend_schema(
        operation_id="review_partial_update",
        description="Partially update an existing review. Only the review owner can update.",
        tags=["Reviews"],
        responses={
            200: OpenApiResponse(description="Review updated successfully."),
            400: OpenApiResponse(description="Invalid input data."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Review not found."),
        },
    ),
    destroy=extend_schema(
        operation_id="review_destroy",
        description="Delete a review. Only the review owner can delete.",
        tags=["Reviews"],
        responses={
            204: OpenApiResponse(description="Review deleted successfully."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Review not found."),
        },
    ),
)
class ReviewViewSet(viewsets.ModelViewSet):
    """
    API endpoint for creating, updating, deleting, and listing reviews for a specific product.
    - **Authentication:** Required for creating, updating, and deleting reviews.
    - **Permissions:**
        - Authenticated users can create reviews for products they have purchased.
        - Only the review owner or a staff member can update or delete a review.
    - **Business Rules:**
        - A user can only leave one review per product.
    """

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        - For 'update', 'partial_update', and 'destroy' actions, only the owner or staff is allowed.
        """
        if self.action in ["update", "partial_update", "destroy"]:
            self.permission_classes = [IsOwnerOrStaff]
        return super().get_permissions()

    def get_queryset(self):
        """
        Returns the queryset of reviews for a specific product, identified by its slug.
        """
        product_slug = self.kwargs.get("product_slug")
        logger.info("Fetching reviews for product slug: %s", product_slug)
        return services.get_reviews_for_product(product_slug)

    def create(self, request, *args, **kwargs):
        """
        Handles the creation of a new review.
        - The review is associated with the authenticated user and the specified product.
        - Delegates the creation logic to the `services.create_review` function.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_slug = self.kwargs.get("product_slug")
        try:
            review = services.create_review(
                user=self.request.user,
                product_slug=product_slug,
                validated_data=serializer.validated_data,
            )
            logger.info(
                "Review created for product slug: %s by user id: %s",
                product_slug,
                self.request.user.id,
            )
            # After creating the review, we serialize it to return in the response.
            response_serializer = self.get_serializer(review)
            headers = self.get_success_headers(response_serializer.data)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers,
            )
        except IntegrityError:
            return Response(
                {"detail": "You have already reviewed this product."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(
                "Error creating review for product slug: %s: %s",
                product_slug,
                e,
                exc_info=True,
            )
            return Response(
                {"detail": "An unexpected server error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema_view(
    list=extend_schema(
        operation_id=r"product\_list",
        description=r"List all products with filtering, ordering, and search capabilities. Cached for 5 minutes.",
        tags=[r"Products"],
        parameters=[
            OpenApiParameter(
                name=r"tag",
                description=r"Filter products by tag slug",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name=r"category",
                description=r"Filter products by category slug",
                required=False,
                type=str,
            ),
        ],
        examples=[
            OpenApiExample(
                r"Example response",
                value={
                    "count": 100,
                    "next": r"http://api.example.com/products/?page=2",
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "name": "Sample Product",
                            "price": "19.99",
                            "stock": 50,
                            "slug": "sample-product",
                        }
                    ],
                },
            )
        ],
    ),
    retrieve=extend_schema(
        operation_id=r"product\_retrieve",
        description=r"Retrieve a single product by slug. Cached for 1 hour.",
        tags=[r"Products"],
        responses={
            200: OpenApiResponse(
                description=r"Product details retrieved successfully."
            ),
            404: OpenApiResponse(description=r"Product not found."),
        },
    ),
    create=extend_schema(
        operation_id=r"product\_create",
        description=r"Create a new product. Requires authentication and ownership/staff status.",
        tags=[r"Products"],
        responses={
            201: OpenApiResponse(description=r"Product created successfully."),
            400: OpenApiResponse(description=r"Invalid input data."),
            401: OpenApiResponse(description=r"Authentication required."),
            403: OpenApiResponse(
                description=r"Permission denied - must be owner or staff."
            ),
        },
    ),
    update=extend_schema(
        operation_id=r"product\_update",
        description=r"Update an existing product. Requires ownership or staff status.",
        tags=[r"Products"],
        responses={
            200: OpenApiResponse(description=r"Product updated successfully."),
            400: OpenApiResponse(description=r"Invalid input data."),
            401: OpenApiResponse(description=r"Authentication required."),
            403: OpenApiResponse(
                description=r"Permission denied - must be owner or staff."
            ),
            404: OpenApiResponse(description=r"Product not found."),
        },
    ),
    partial_update=extend_schema(
        operation_id=r"product\_partial\_update",
        description=r"Partially update an existing product. Requires ownership or staff status.",
        tags=[r"Products"],
        responses={
            200: OpenApiResponse(description=r"Product updated successfully."),
            400: OpenApiResponse(description=r"Invalid input data."),
            401: OpenApiResponse(description=r"Authentication required."),
            403: OpenApiResponse(
                description=r"Permission denied - must be owner or staff."
            ),
            404: OpenApiResponse(description=r"Product not found."),
        },
    ),
    destroy=extend_schema(
        operation_id=r"product\_destroy",
        description=r"Delete a product. Requires ownership or staff status.",
        tags=[r"Products"],
        responses={
            204: OpenApiResponse(description=r"Product deleted successfully."),
            401: OpenApiResponse(description=r"Authentication required."),
            403: OpenApiResponse(
                description=r"Permission denied - must be owner or staff."
            ),
            404: OpenApiResponse(description=r"Product not found."),
        },
    ),
    list_user_products=extend_schema(
        operation_id=r"product\_list\_user",
        description=r"List products belonging to the authenticated user or a specified user by username. Cached for 1 week.",
        tags=[r"Products"],
        parameters=[
            OpenApiParameter(
                name="username",
                description="Filter products by the username of the user. Optional.",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(description=r"User products retrieved successfully."),
            401: OpenApiResponse(description=r"Authentication required."),
        },
    ),
)
class ProductViewSet(PaginationMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing products.
    - **Authentication:** Read-only for anonymous users, while authenticated users can perform all actions.
    - **Permissions:**
        - Product creation, update, and deletion are restricted to the product owner or staff members.
    - **Features:**
        - Supports filtering by category, tags, and stock status.
        - Supports ordering by name, price, stock, and creation date.
        - Includes a product recommendation feature.
    """

    queryset = Product.objects.select_related("user", "category").prefetch_related(
        "tags", "reviews"
    )
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrStaff]
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
        InStockFilterBackend,
        ProductSearchFilterBackend,
    ]
    ordering_fields = [r"name", r"price", r"stock", r"created"]
    lookup_field = r"slug"

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        - The 'list_user_products' action is available to any user.
        """
        if self.action in [r"list_user_products"]:
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()

    def get_serializer_class(self):
        """
        Returns the serializer class to be used for the current action.
        - For the 'retrieve' action, it uses the `ProductDetailSerializer` to include more details.
        """
        if self.action == "retrieve":
            return ProductDetailSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        """
        Handles the creation of a new product, associating it with the authenticated user.
        """
        try:
            serializer.save(user=self.request.user)
            cache.delete("product_list")
            logger.info("Product created by user id: %s", self.request.user.id)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                "Error creating product for user id: %s: %s",
                self.request.user.id,
                e,
                exc_info=True,
            )
            return Response(
                {"detail": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def perform_update(self, serializer):
        """
        Handles the update of a product.
        """
        serializer.save()
        cache.delete(f"product_{serializer.instance.slug}")
        cache.delete("product_list")

    def perform_destroy(self, instance):
        """
        Handles the deletion of a product.
        """
        cache.delete(f"product_{instance.slug}")
        cache.delete("product_list")
        instance.delete()

    def list(self, request, *args, **kwargs):
        """
        Lists all products with caching.
        - Caches the entire product list for 5 minutes.
        - **Note:** This caching strategy will be improved to be more granular.
        """
        # A more granular caching strategy will be implemented in the caching step.
        query_params = request.query_params.urlencode()
        cache_key = f"product_list_{query_params}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60 * 5)  # 5 minutes
        return response

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieves a single product by its slug.
        - Delegates the retrieval logic to the `services.get_product_detail` function.
        """
        slug = kwargs.get("slug")
        cache_key = f"product_{slug}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        product = services.get_product_detail(slug)
        serializer = self.get_serializer(product)
        cache.set(cache_key, serializer.data, 60 * 60)  # 1 hour
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="user-products",
        url_name="user-products",
    )
    def list_user_products(self, request):
        """
        A custom action to list products belonging to a specific user.
        - If a 'username' is provided in the query parameters, it lists products for that user.
        - Otherwise, it lists products for the authenticated user.
        """
        try:
            logger.info("Listing user products for user id: %s", request.user.id)
            username = request.query_params.get("username")
            user = request.user if not username else None
            if not user and not username:
                return Response(
                    {"detail": "Authentication required to view your products."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            queryset = services.get_user_products(user=user, username=username)
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error("Error listing user products: %s", e, exc_info=True)
            return Response(
                {"detail": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema_view(
    list=extend_schema(
        operation_id=r"category\_list",
        description=r"List all product categories. Publicly accessible. Cached for 24 hours.",
        tags=[r"Categories"],
        responses={
            200: OpenApiResponse(description=r"Categories retrieved successfully."),
        },
    ),
    retrieve=extend_schema(
        operation_id=r"category\_retrieve",
        description=r"Retrieve a single category by slug.",
        tags=[r"Categories"],
        responses={
            200: OpenApiResponse(
                description=r"Category details retrieved successfully."
            ),
            404: OpenApiResponse(description=r"Category not found."),
        },
    ),
    create=extend_schema(
        operation_id=r"category\_create",
        description=r"Create a new category. Requires admin privileges.",
        tags=[r"Categories"],
        responses={
            201: OpenApiResponse(description=r"Category created successfully."),
            400: OpenApiResponse(description=r"Invalid input data."),
            401: OpenApiResponse(description=r"Authentication required."),
            403: OpenApiResponse(description=r"Admin privileges required."),
        },
    ),
    update=extend_schema(
        operation_id=r"category\_update",
        description=r"Update an existing category. Requires admin privileges.",
        tags=[r"Categories"],
        responses={
            200: OpenApiResponse(description=r"Category updated successfully."),
            400: OpenApiResponse(description=r"Invalid input data."),
            401: OpenApiResponse(description=r"Authentication required."),
            403: OpenApiResponse(description=r"Admin privileges required."),
            404: OpenApiResponse(description=r"Category not found."),
        },
    ),
    partial_update=extend_schema(
        operation_id=r"category\_partial\_update",
        description=r"Partially update an existing category. Requires admin privileges.",
        tags=[r"Categories"],
        responses={
            200: OpenApiResponse(description=r"Category updated successfully."),
            400: OpenApiResponse(description=r"Invalid input data."),
            401: OpenApiResponse(description=r"Authentication required."),
            403: OpenApiResponse(description=r"Admin privileges required."),
            404: OpenApiResponse(description=r"Category not found."),
        },
    ),
    destroy=extend_schema(
        operation_id=r"category\_destroy",
        description=r"Delete a category. Requires admin privileges.",
        tags=[r"Categories"],
        responses={
            204: OpenApiResponse(description=r"Category deleted successfully."),
            401: OpenApiResponse(description=r"Authentication required."),
            403: OpenApiResponse(description=r"Admin privileges required."),
            404: OpenApiResponse(description=r"Category not found."),
        },
    ),
)
class CategoryViewSet(PaginationMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing product categories.
    - **Authentication:** Read-only for anonymous users.
    - **Permissions:**
        - Category creation, update, and deletion are restricted to admin users.
    """

    queryset = Category.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    lookup_field = r"slug"

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        - 'list' and 'retrieve' actions are allowed for any user.
        - Other actions require admin privileges.
        """
        if self.action in ["list", "retrieve"]:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()

    def get_queryset(self):
        """
        Caches the queryset for 24 hours.
        """
        return cache.get_or_set("category_list", Category.objects.all(), 60 * 60 * 24)
