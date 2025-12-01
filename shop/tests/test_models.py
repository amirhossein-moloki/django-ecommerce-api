from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from shop.models import Category, Product, Review
from orders.models import Order, OrderItem
from shop import services
from decimal import Decimal

User = get_user_model()


class CategoryModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')

    def test_category_creation(self):
        category = Category.objects.create(name='Test Category')
        self.assertEqual(category.name, 'Test Category')
        self.assertEqual(category.slug, 'test-category')

    def test_category_str(self):
        category = Category.objects.create(name='Test Category')
        self.assertEqual(str(category), 'Category: Test Category')

    def test_get_absolute_url(self):
        category = Category.objects.create(name='Test Category')
        self.assertEqual(category.get_absolute_url(), f'/api/v1/categories/{category.slug}/')


class ProductModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        self.category = Category.objects.create(name='Test Category')

    def test_product_creation(self):
        product = Product.objects.create(
            name='Test Product',
            description='A test product.',
            price=10.00,
            stock=5,
            category=self.category,
            user=self.user,
            weight=1.0,
            length=1.0,
            width=1.0,
            height=1.0
        )
        self.assertEqual(product.name, 'Test Product')
        self.assertTrue(product.slug.startswith('test-product'))

    def test_in_stock_manager(self):
        product1 = Product.objects.create(
            name='Product 1', price=10, stock=5, category=self.category, user=self.user, weight=1, length=1, width=1, height=1)
        product2 = Product.objects.create(
            name='Product 2', price=20, stock=0, category=self.category, user=self.user, weight=1, length=1, width=1, height=1)
        self.assertIn(product1, Product.in_stock.all())
        self.assertNotIn(product2, Product.in_stock.all())

    def test_product_str(self):
        product = Product.objects.create(
            name='Test Product', price=10, stock=5, category=self.category, user=self.user, weight=1, length=1, width=1, height=1)
        self.assertEqual(str(product), f'Product: Test Product (ID: {product.product_id})')

    def test_get_absolute_url(self):
        product = Product.objects.create(
            name='Test Product', price=10, stock=5, category=self.category, user=self.user, weight=1, length=1, width=1, height=1)
        self.assertEqual(product.get_absolute_url(), f'/api/v1/products/{product.slug}/')


class ReviewModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            price=10.00,
            stock=5,
            category=self.category,
            user=self.user1,
            weight=1.0,
            length=1.0,
            width=1.0,
            height=1.0
        )
        self.order = Order.objects.create(user=self.user1)
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1)

    def test_review_creation(self):
        Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            comment='Great product!'
        )
        self.assertEqual(Review.objects.count(), 1)

    def test_review_unique_constraint(self):
        Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            comment='Great product!'
        )
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                product=self.product,
                user=self.user1,
                rating=4,
                comment='Another review.'
            )


    def test_review_str(self):
        review = Review.objects.create(
            product=self.product,
            user=self.user1,
            rating=5,
            comment='Great product!'
        )
        self.assertEqual(str(review), f'Review by {self.user1} for {self.product} - {review.rating} stars')

class ShopServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='password'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=Decimal('10.00'),
            category=self.category,
            stock=10,
            user=self.user
        )
        self.order = Order.objects.create(user=self.user, status=Order.Status.PAID)
        self.order_item = OrderItem.objects.create(order=self.order, product=self.product, quantity=1)

    def test_create_review(self):
        review = services.create_review(
            user=self.user,
            product_slug=self.product.slug,
            validated_data={'rating': 4, 'comment': 'Great!'}
        )
        self.assertEqual(review.rating, 4)
