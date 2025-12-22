from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from shop.models import Product, Category, ProductVariant
from chat.models import Message

User = get_user_model()


class ChatTestCase(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com',
            username='seller',
            password='password',
            phone_number='1111111111'
        )
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            username='buyer',
            password='password',
            phone_number='2222222222'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            user=self.seller
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            price=10.00,
            stock=10
        )
        self.message = Message.objects.create(
            sender=self.buyer,
            recipient=self.seller,
            product=self.product,
            content='Test message'
        )

    def test_message_model_str(self):
        message_str = str(self.message)
        self.assertIn(self.buyer.username, message_str)
        self.assertIn(self.seller.username, message_str)
        self.assertIn(self.product.name, message_str)


class ProductChatAPIViewTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com',
            username='seller',
            password='password',
            phone_number='3333333333'
        )
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            username='buyer',
            password='password',
            phone_number='4444444444'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            user=self.seller
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            price=10.00,
            stock=10
        )
        self.url = reverse('api-v1:product-chat', kwargs={'product_id': self.product.product_id})

    def test_get_chat_messages_authenticated(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_chat_messages_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
