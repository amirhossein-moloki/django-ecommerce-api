import json
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from shop.models import Product, Category
from chat.models import Message
from chat.consumers import ChatConsumer
from ecommerce_api.asgi import application

User = get_user_model()


class ChatTestCase(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com',
            username='seller',
            password='password'
        )
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            username='buyer',
            password='password'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=10.00,
            category=self.category,
            stock=10,
            user=self.seller
        )
        self.message = Message.objects.create(
            sender=self.buyer,
            recipient=self.seller,
            product=self.product,
            content='Test message'
        )

    def test_message_model_str(self):
        self.assertIn('buyer to seller about Test Product', str(self.message))


class ProductChatAPIViewTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@example.com',
            username='seller',
            password='password'
        )
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            username='buyer',
            password='password'
        )
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=10.00,
            category=self.category,
            stock=10,
            user=self.seller
        )
        self.url = reverse('api-v1:product-chat', kwargs={'product_id': self.product.product_id})

    def test_get_chat_messages_authenticated(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_chat_messages_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChatConsumerTests(TestCase):
    async def test_chat_consumer(self):
        seller = await User.objects.acreate_user(
            email='seller@example.com',
            username='seller',
            password='password'
        )
        buyer = await User.objects.acreate_user(
            email='buyer@example.com',
            username='buyer',
            password='password'
        )
        category = await Category.objects.acreate(name='Test Category', slug='test-category')
        product = await Product.objects.acreate(
            name='Test Product',
            slug='test-product',
            price=10.00,
            category=category,
            stock=10,
            user=seller
        )

        communicator = WebsocketCommunicator(
            application,
            f'/ws/chat/{product.product_id}/'
        )
        communicator.scope['user'] = buyer
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_to(text_data=json.dumps({'message': 'Hello'}))
        response = await communicator.receive_from()
        self.assertIn('message_sent', response)

        await communicator.disconnect()
