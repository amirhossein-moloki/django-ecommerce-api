
import pytest
from django.urls import reverse
from rest_framework import status
from orders.factories import OrderFactory
from account.factories import UserFactory, AddressFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def order(db):
    user = UserFactory.create()
    address = AddressFactory.create(user=user)
    return OrderFactory.create(user=user, address=address)


class TestShippingAPI:
    def test_city_list(self, api_client, user, requests_mock):
        requests_mock.get("https://api.postex.ir/api/v1/locality/cities/all", json={'data': [{'name': 'Tehran'}]})

        api_client.force_authenticate(user=user)
        url = reverse('shipping:city-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['data'][0]['name'] == 'Tehran'

    def test_calculate_shipping_cost(self, api_client, user, order, requests_mock):
        requests_mock.post("https://api.postex.ir/api/v1/shipping/quotes", json={'data': [{'price': 15000}]})

        api_client.force_authenticate(user=user)
        url = reverse('shipping:calculate-cost')
        data = {'order_id': str(order.order_id)}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['data'][0]['price'] == 15000
