import pytest
from django.db.utils import IntegrityError
from shop.models import Category, Product, Review
from shop.factories import CategoryFactory, ProductFactory, ReviewFactory, UserFactory, ProductVariantFactory
from orders.factories import OrderFactory, OrderItemFactory
from shop import services

pytestmark = pytest.mark.django_db


class TestCategoryModel:
    def test_category_creation(self):
        category = CategoryFactory(name='Test Category')
        assert category.name == 'Test Category'
        assert category.slug == 'test-category'

    def test_category_str(self):
        category = CategoryFactory(name='Test Category')
        assert str(category) == 'Category: Test Category'

    def test_get_absolute_url(self):
        category = CategoryFactory(name='Test Category')
        assert category.get_absolute_url() == f'/api/v1/categories/{category.slug}/'


class TestProductModel:
    def test_product_creation(self):
        product = ProductFactory(name='Test Product')
        assert product.name == 'Test Product'
        assert product.slug.startswith('test-product')
        assert product.variants.count() == 1
        variant = product.variants.first()
        assert variant.price == '100.00'
        assert variant.stock == 10

    def test_soft_delete_and_restore(self):
        product = ProductFactory()
        assert product in Product.objects.all()
        product.delete()
        assert product not in Product.objects.all()
        assert product in Product.all_objects.all()
        product.restore()
        assert product in Product.objects.all()

    def test_product_str(self):
        product = ProductFactory(name='Test Product')
        assert str(product) == f'Product: Test Product (ID: {product.product_id})'

    def test_get_absolute_url(self):
        product = ProductFactory(name='Test Product')
        assert product.get_absolute_url() == f'/api/v1/products/{product.slug}/'


class TestReviewModel:
    def test_review_creation(self):
        review = ReviewFactory(rating=5, comment='Great product!')
        assert Review.objects.count() == 1
        assert review.rating == 5

    def test_review_unique_constraint(self):
        user = UserFactory()
        product = ProductFactory()
        ReviewFactory(user=user, product=product)
        with pytest.raises(IntegrityError):
            ReviewFactory(user=user, product=product)

    def test_review_str(self):
        review = ReviewFactory(rating=5)
        assert str(review) == f'Review by {review.user} for {review.product} - {review.rating} stars'


class TestShopServices:
    def test_create_review(self):
        user = UserFactory()
        product = ProductFactory()
        variant = product.variants.first()
        order = OrderFactory(user=user, status='paid')
        OrderItemFactory(order=order, variant=variant)

        review = services.create_review(
            user=user,
            product_slug=product.slug,
            validated_data={'rating': 4, 'comment': 'Great!'}
        )
        assert review.rating == 4
