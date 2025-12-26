import pytest
from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied, ValidationError

from account.tests.factories import UserFactory
from orders.models import Order
from orders.tests.factories import OrderFactory, OrderItemFactory
from shop import services
from shop.models import Category
from shop.tests.factories import (
    ProductFactory,
    CategoryFactory,
    ReviewFactory,
    ProductVariantFactory,
)

pytestmark = pytest.mark.django_db


class TestProductServices:
    def test_get_product_detail_caching(self):
        product = ProductFactory()
        cache_key = f"product_detail_{product.slug}"
        cache.delete(cache_key)

        services.get_product_detail(product.slug)
        assert cache.get(cache_key) is not None
        cache.delete(cache_key)

    def test_get_user_products(self):
        user1 = UserFactory()
        user2 = UserFactory()
        ProductFactory.create_batch(3, user=user1)
        ProductFactory.create_batch(2, user=user2)

        assert services.get_user_products(user=user1).count() == 3
        assert (
            services.get_user_products(user=None, username=user2.username).count() == 2
        )


class TestReviewServices:
    def test_create_review_requires_paid_order(self):
        user = UserFactory()
        product = ProductFactory()

        with pytest.raises(PermissionDenied):
            services.create_review(
                user, product.slug, {"rating": 5, "comment": "Great!"}
            )

    def test_create_review_success(self):
        user = UserFactory()
        product = ProductFactory()
        order = OrderFactory(user=user)
        order.status = Order.Status.PAID
        order.save(update_fields=["status"])
        variant = ProductVariantFactory(product=product)
        OrderItemFactory(order=order, variant=variant)

        review = services.create_review(
            user, product.slug, {"rating": 5, "comment": "Awesome!"}
        )
        assert review.product == product


class TestCategoryServices:
    def test_create_category_duplicate_name(self):
        CategoryFactory(name="Electronics")
        with pytest.raises(ValidationError):
            services.create_category({"name": "Electronics"})
