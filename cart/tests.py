from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from datetime import timedelta
from shop.models import Product, Category
from coupons.models import Coupon
from cart.cart import Cart
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class CartClassTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='testuser@example.com',
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
        self.coupon = Coupon.objects.create(
            code='TESTCOUPON',
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=1),
            discount=10,
            active=True
        )

    def test_cart_add_product_anonymous(self):
        request = self.factory.get('/')
        request.session = self.client.session
        request.user = AnonymousUser()
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)
        self.assertEqual(len(cart), 1)
        self.assertEqual(cart.get_total_price(), Decimal('10.00'))

    def test_cart_add_product_authenticated(self):
        request = self.factory.get('/')
        request.user = self.user
        request.session = self.client.session
        cart = Cart(request)
        cart.add(product=self.product, quantity=2)
        self.assertEqual(len(cart), 2)
        self.assertEqual(cart.get_total_price(), Decimal('20.00'))

    def test_cart_remove_product_anonymous(self):
        request = self.factory.get('/')
        request.session = self.client.session
        request.user = AnonymousUser()
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)
        cart.remove(product=self.product)
        self.assertEqual(len(cart), 0)

    def test_cart_remove_product_authenticated(self):
        request = self.factory.get('/')
        request.user = self.user
        request.session = self.client.session
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)
        cart.remove(product=self.product)
        self.assertEqual(len(cart), 0)

    def test_cart_clear_anonymous(self):
        request = self.factory.get('/')
        request.session = self.client.session
        request.user = AnonymousUser()
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)
        cart.clear()
        self.assertEqual(len(cart), 0)

    def test_cart_clear_authenticated(self):
        request = self.factory.get('/')
        request.user = self.user
        request.session = self.client.session
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)
        cart.clear()
        self.assertEqual(len(cart), 0)

    def test_cart_coupon_anonymous(self):
        request = self.factory.get('/')
        request.session = self.client.session
        request.user = AnonymousUser()
        request.session['coupon_id'] = self.coupon.id
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)
        self.assertEqual(cart.get_discount(), Decimal('1.00'))
        self.assertEqual(cart.get_total_price_after_discount(), Decimal('9.00'))

    def test_cart_coupon_authenticated(self):
        request = self.factory.get('/')
        request.user = self.user
        request.session = self.client.session
        cart = Cart(request)
        cart.cart.coupon = self.coupon
        cart.cart.save()
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)
        self.assertEqual(cart.get_discount(), Decimal('1.00'))
        self.assertEqual(cart.get_total_price_after_discount(), Decimal('9.00'))

    def test_merge_session_cart(self):
        request = self.factory.get('/')
        request.session = self.client.session
        request.user = AnonymousUser()
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)

        request.user = self.user
        cart = Cart(request)
        cart.merge_session_cart()
        self.assertEqual(len(cart), 1)


class CartViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
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
        self.coupon = Coupon.objects.create(
            code='TESTCOUPON',
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=1),
            discount=10,
            active=True
        )
        self.add_url = reverse('api-v1:cart-add', kwargs={'product_id': self.product.product_id})
        self.remove_url = reverse('api-v1:cart-remove', kwargs={'product_id': self.product.product_id})
        self.clear_url = reverse('api-v1:cart-clear')
        self.list_url = reverse('api-v1:cart-list')

    def test_cart_add_product_anonymous(self):
        response = self.client.post(self.add_url, {'quantity': 1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cart_add_product_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.add_url, {'quantity': 2}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cart_remove_product_anonymous(self):
        self.client.post(self.add_url, {'quantity': 1}, format='json')
        response = self.client.delete(self.remove_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cart_remove_product_authenticated(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(self.add_url, {'quantity': 1}, format='json')
        response = self.client.delete(self.remove_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cart_clear_anonymous(self):
        self.client.post(self.add_url, {'quantity': 1}, format='json')
        response = self.client.delete(self.clear_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cart_clear_authenticated(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(self.add_url, {'quantity': 1}, format='json')
        response = self.client.delete(self.clear_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_cart(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
