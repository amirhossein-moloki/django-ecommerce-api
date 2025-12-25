import pytest
from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied, ValidationError

from account.tests.factories import UserFactory
from orders.models import Order
from orders.tests.factories import OrderFactory, OrderItemFactory
from shop import services
from shop.models import Category
from shop.tests.factories import ProductFactory, CategoryFactory, ReviewFactory

pytestmark = pytest.mark.django_db


class TestProductServices:
    def test_get_product_detail_caching(self):
        """
        Tests that product detail retrieval is cached.
        """
        product = ProductFactory()
        cache_key = f"product_detail_{product.slug}"
        cache.delete(cache_key)  # Ensure cache is clean

        # First call, should hit DB and set cache
        retrieved_product = services.get_product_detail(product.slug)
        assert retrieved_product == product
        assert cache.get(cache_key) is not None

        # Second call, should hit cache
        # To prove it's from cache, let's delete the product and see if we can still get it
        product.delete()
        cached_product = services.get_product_detail(product.slug)
        assert cached_product is not None

        cache.delete(cache_key) # Clean up

    def test_get_user_products(self):
        """
        Tests retrieving products for a specific user.
        """
        user1 = UserFactory()
        user2 = UserFactory()
        ProductFactory.create_batch(3, user=user1)
        ProductFactory.create_batch(2, user=user2)

        user1_products = services.get_user_products(user=user1)
        assert user1_products.count() == 3

        user2_products_by_username = services.get_user_products(
            user=None, username=user2.username
        )
        assert user2_products_by_username.count() == 2


class TestReviewServices:
    def test_get_reviews_for_product(self):
        """
        Tests retrieving reviews for a specific product.
        """
        product = ProductFactory()
        ReviewFactory.create_batch(5, product=product)
        # Create reviews for other products that should not be returned
        ReviewFactory.create_batch(3)

        reviews = services.get_reviews_for_product(product.slug)
        assert reviews.count() == 5

    def test_create_review_requires_paid_order(self):
        """
        Tests that a user must have a paid order for a product to review it.
        """
        user = UserFactory()
        product = ProductFactory()

        # Case 1: No order exists
        with pytest.raises(PermissionDenied):
            services.create_review(
                user, product.slug, {"rating": 5, "comment": "Great!"}
            )

        # Case 2: Order exists but is not paid
        order = OrderFactory(user=user, status=Order.Status.PENDING)
        OrderItemFactory(order=order, variant__product=product)
        with pytest.raises(PermissionDenied):
            services.create_review(
                user, product.slug, {"rating": 5, "comment": "Still great!"}
            )

    def test_create_review_success(self):
        """
        Tests successful review creation when a paid order exists.
        """
        user = UserFactory()
        product = ProductFactory()
        order = OrderFactory(user=user, status=Order.Status.PAID)
        OrderItemFactory(order=order, variant__product=product)

        review = services.create_review(
            user, product.slug, {"rating": 5, "comment": "Awesome!"}
        )
        assert review is not None
        assert review.user == user
        assert review.product == product
        assert review.rating == 5


class TestCategoryServices:
    def test_get_category_list(self):
        """
        Tests retrieving the list of all categories.
        """
        CategoryFactory.create_batch(10)
        categories = services.get_category_list()
        assert categories.count() == 10

    def test_create_category_duplicate_name(self):
        """
        Tests that creating a category with a duplicate name raises a ValidationError.
        """
        CategoryFactory(name="Electronics")
        with pytest.raises(ValidationError):
            services.create_category({"name": "Electronics"})

    def test_create_category_success(self):
        """
        Tests successful category creation.
        """
        category_data = {"name": "Books"}
        category = services.create_category(category_data)
        assert category is not None
        assert category.name == "Books"
        assert Category.objects.count() == 1
