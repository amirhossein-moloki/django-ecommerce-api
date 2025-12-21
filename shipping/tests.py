import pytest
from unittest.mock import patch
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from orders.factories import OrderFactory
from account.factories import UserFactory, AddressFactory

pytestmark = pytest.mark.django_db


class TestShippingProvider:
    @patch('shipping.providers.requests.post')
    def test_postex_create_shipment(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'status': 'success'}
        from shipping.providers import PostexShippingProvider
        provider = PostexShippingProvider()
        user = UserFactory.create()
        address = AddressFactory.create(user=user, city_code=1)
        order = OrderFactory.create(user=user, address=address, total_payable=Decimal('100.00'))
        response = provider.create_shipment(order)
        assert response['status'] == 'success'


class TestShippingAPI:
    @patch('shipping.providers.PostexShippingProvider.get_cities')
    def test_city_list(self, mock_get_cities, api_client, user):
        mock_get_cities.return_value = {'data': [{'name': 'Tehran'}]}
        api_client.force_authenticate(user=user)
        url = reverse('shipping:city-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    @patch('shipping.providers.PostexShippingProvider.get_shipping_quote')
    def test_calculate_shipping_cost(self, mock_get_quote, api_client, user):
        mock_get_quote.return_value = {'data': [{'price': 15000}]}
        api_client.force_authenticate(user=user)
        order = OrderFactory.create(user=user)
        url = reverse('shipping:calculate-cost')
        data = {'order_id': str(order.order_id)}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
