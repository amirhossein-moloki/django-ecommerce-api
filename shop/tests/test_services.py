import pytest
from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied
from shop.services import get_product_detail, get_user_products, create_review
from shop.factories import ProductFactory, ProductVariantFactory
from account.factories import UserFactory
from orders.factories import OrderFactory, OrderItemFactory
from orders.models import Order

pytestmark = pytest.mark.django_db


class TestShopServices:
    def test_get_product_detail_caching(self, django_assert_num_queries):
        product = ProductFactory()
        # Clear cache before test
        cache.clear()

        # First call, should hit DB and cache it
        p1 = get_product_detail(slug=product.slug)
        assert p1 == product

        # Second call, should hit cache
        with django_assert_num_queries(0):
            p2 = get_product_detail(slug=product.slug)
            assert p2 == product

        # Clear cache after test
        cache.clear()

    def test_get_user_products(self):
        user1 = UserFactory()
        user2 = UserFactory()
        ProductFactory.create_batch(3, user=user1)
        ProductFactory.create_batch(2, user=user2)

        products1 = get_user_products(user=user1)
        assert products1.count() == 3

        products2 = get_user_products(user=user2)
        assert products2.count() == 2

    def test_create_review_success(self):
        user = UserFactory()
        variant = ProductVariantFactory()
        product = variant.product
        order = OrderFactory(user=user, status=Order.Status.PAID)
        OrderItemFactory(order=order, variant=variant)

        review_data = {'rating': 5, 'comment': 'Excellent!'}
        review = create_review(user=user, product_slug=product.slug, validated_data=review_data)
        assert review.rating == 5
        assert review.user == user
        assert review.product == product

    def test_create_review_permission_denied_if_not_purchased(self):
        user = UserFactory()
        product = ProductFactory()

        with pytest.raises(PermissionDenied):
            review_data = {'rating': 5, 'comment': 'Excellent!'}
            create_review(user=user, product_slug=product.slug, validated_data=review_data)
