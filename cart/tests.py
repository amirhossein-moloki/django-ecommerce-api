from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from shop.models import Product, Category
from .models import Cart, CartItem

User = get_user_model()


class CartTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            price=10.00,
            stock=10,
            user=self.user,
            weight=1.0,
            length=1.0,
            width=1.0,
            height=1.0
        )
        self.client = APIClient()

    def test_add_to_cart_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api-v1:cart-add-to-cart', kwargs={'product_id': self.product.product_id})
        data = {'quantity': 2}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart = Cart.objects.get(user=self.user)
        cart_item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(cart_item.quantity, 2)

    def test_add_to_cart_anonymous(self):
        url = reverse('api-v1:cart-add-to-cart', kwargs={'product_id': self.product.product_id})
        data = {'quantity': 2}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.session['cart'][str(self.product.product_id)]['quantity'], 2)

    def test_remove_from_cart_authenticated(self):
        self.client.force_authenticate(user=self.user)
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        url = reverse('api-v1:cart-remove-from-cart', kwargs={'product_id': self.product.product_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CartItem.objects.filter(cart=cart, product=self.product).exists())

    def test_clear_cart_authenticated(self):
        self.client.force_authenticate(user=self.user)
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        url = reverse('api-v1:cart-clear-cart')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(cart.items.count(), 0)

    def test_merge_cart_on_login(self):
        # Add to cart as anonymous
        url = reverse('api-v1:cart-add-to-cart', kwargs={'product_id': self.product.product_id})
        data = {'quantity': 2}
        self.client.post(url, data)

        # Log in
        self.client.force_authenticate(user=self.user)

        # The cart should be merged
        cart = Cart.objects.get(user=self.user)
        cart_item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(cart_item.quantity, 2)
        self.assertNotIn('cart', self.client.session)

    def test_clear_cart_anonymous(self):
        # Add to cart first
        url = reverse('api-v1:cart-add-to-cart', kwargs={'product_id': self.product.product_id})
        data = {'quantity': 2}
        self.client.post(url, data)

        # Then clear
        url = reverse('api-v1:cart-clear-cart')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn('cart', self.client.session)
