from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from orders.models import Order
from account.models import Address

User = get_user_model()


class ShippingProviderTests(TestCase):
    @patch('shipping.providers.requests.post')
    def test_postex_create_shipment(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'status': 'success'}
        from shipping.providers import PostexShippingProvider
        provider = PostexShippingProvider()
        user = User.objects.create(username='testuser')
        address = Address.objects.create(user=user, city_code=1)
        order = Order.objects.create(user=user, address=address, total_payable=Decimal('100.00'))
        response = provider.create_shipment(order)
        self.assertEqual(response['status'], 'success')

    @patch('shipping.providers.requests.get')
    def test_postex_get_shipment_tracking(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'status': 'success'}
        from shipping.providers import PostexShippingProvider
        provider = PostexShippingProvider()
        response = provider.get_shipment_tracking('12345')
        self.assertEqual(response['status'], 'success')

    @patch('shipping.providers.requests.post')
    def test_postex_get_shipping_quote(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'data': [{'price': 15000}]}
        from shipping.providers import PostexShippingProvider
        provider = PostexShippingProvider()
        user = User.objects.create(username='testuser')
        address = Address.objects.create(user=user, city_code=1)
        order = Order.objects.create(user=user, address=address, total_payable=Decimal('100.00'))
        response = provider.get_shipping_quote(order)
        self.assertEqual(response['data'][0]['price'], 15000)

    @patch('shipping.providers.requests.delete')
    def test_postex_cancel_shipment(self, mock_delete):
        mock_delete.return_value.status_code = 200
        mock_delete.return_value.json.return_value = {'status': 'success'}
        from shipping.providers import PostexShippingProvider
        provider = PostexShippingProvider()
        response = provider.cancel_shipment('12345')
        self.assertEqual(response['status'], 'success')

    @patch('shipping.providers.requests.get')
    def test_postex_get_cities(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{'name': 'Tehran'}]
        from shipping.providers import PostexShippingProvider
        provider = PostexShippingProvider()
        response = provider.get_cities()
        self.assertEqual(response[0]['name'], 'Tehran')


class ShippingAPIViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+989123456712',
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
        self.order = Order.objects.create(user=self.user, address=self.address, total_payable=Decimal('100.00'))
        self.city_list_url = reverse('shipping:city-list')
        self.calculate_shipping_url = reverse('shipping:calculate-cost')

    @patch('shipping.providers.PostexShippingProvider.get_cities')
    def test_city_list(self, mock_get_cities):
        mock_get_cities.return_value = {'data': [{'name': 'Tehran'}]}
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.city_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('shipping.providers.PostexShippingProvider.get_shipping_quote')
    def test_calculate_shipping_cost(self, mock_get_quote):
        mock_get_quote.return_value = {'data': [{'price': 15000}]}
        self.client.force_authenticate(user=self.user)
        data = {'order_id': str(self.order.order_id)}
        response = self.client.post(self.calculate_shipping_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
