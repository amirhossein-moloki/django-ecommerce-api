from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from shop.models import Product, Category
from coupons.models import Coupon
from orders.models import Order, OrderItem
from account.models import Address
from django.urls import reverse

User = get_user_model()


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='password'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product1 = Product.objects.create(
            name='Test Product 1',
            slug='test-product-1',
            price=Decimal('10.00'),
            category=self.category,
            stock=10,
            user=self.user
        )
        self.product2 = Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            price=Decimal('20.00'),
            category=self.category,
            stock=10,
            user=self.user
        )
        self.coupon = Coupon.objects.create(
            code='TESTCOUPON',
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=1),
            discount=10,
            active=True
        )
        self.order = Order.objects.create(user=self.user, coupon=self.coupon)
        self.order_item1 = OrderItem.objects.create(order=self.order, product=self.product1, quantity=1)
        self.order_item2 = OrderItem.objects.create(order=self.order, product=self.product2, quantity=2)

    def test_get_total_cost_before_discount(self):
        self.assertEqual(self.order.get_total_cost_before_discount(), Decimal('50.00'))

    def test_get_discount(self):
        self.assertEqual(self.order.get_discount(), Decimal('5.00'))

    def test_total_price(self):
        self.assertEqual(self.order.total_price, Decimal('45.00'))


class OrderViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='password'
        )
        self.address = Address.objects.create(
            user=self.user,
            province='Tehran',
            city='Tehran',
            postal_code='1234567890',
            full_address='123 Main St'
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
        self.create_url = reverse('api-v1:order-list')

    def test_create_order(self):
        self.client.force_authenticate(user=self.user)
        # Add item to cart
        self.client.post(reverse('api-v1:cart-add', kwargs={'product_id': self.product.product_id}), {'quantity': 1}, format='json')
        data = {'address_id': self.address.id}
        response = self.client.post(self.create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class OrderIntegrationTest(APITestCase):
    """
    Integration test for the complete order process.
    """

    def setUp(self):
        """
        Set up the necessary objects for the test.
        """
        # Create a user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='User',
            username='testuser'
        )
        self.user.is_active = True
        self.user.save()

        # Create a category
        self.category = Category.objects.create(name='Electronics', slug='electronics')

        # Create a product
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            price=Decimal('100.00'),
            stock=10,
            user=self.user,
            weight=1.0,
            length=1.0,
            width=1.0,
            height=1.0
        )

        # Create a coupon
        self.coupon = Coupon.objects.create(
            code='TESTCODE',
            discount=20,  # 20% discount
            active=True,
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=1)
        )

        # Create an address
        self.address = Address.objects.create(
            user=self.user,
            province='Tehran',
            city='Tehran',
            postal_code='1234567890',
            full_address='Azadi St.',
            receiver_name='Test User',
            receiver_phone='09123456789'
        )

    def test_add_to_cart_apply_coupon_create_order(self):
        """
        Test the full workflow:
        1. Add a product to the cart.
        2. Apply a valid coupon.
        3. Create an order.
        4. Verify the order details and stock reduction.
        """
        # Authenticate the user
        self.client.force_authenticate(user=self.user)

        # 1. Add product to cart
        add_to_cart_url = reverse('api-v1:cart-add', kwargs={'product_id': self.product.product_id})
        response = self.client.post(add_to_cart_url, {'quantity': 2, 'override': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 2. Apply coupon
        apply_coupon_url = reverse('api-v1:coupon-apply-coupon')
        response = self.client.post(apply_coupon_url, {'code': self.coupon.code}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3. Create order
        create_order_url = reverse('api-v1:order-list')
        order_data = {'address_id': self.address.id, 'coupon_code': self.coupon.code}
        response = self.client.post(create_order_url, order_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 4. Verify the order
        self.assertEqual(response.data['coupon'], self.coupon.code)

        # Check subtotal (2 * 100)
        self.assertEqual(Decimal(response.data['subtotal']), Decimal('200.00'))

        # Check discount (20% of 200)
        self.assertEqual(Decimal(response.data['discount_amount']), Decimal('40.00'))

        # Verify stock reduction
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
