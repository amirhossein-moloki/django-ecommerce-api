import pytest
from unittest.mock import patch
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from orders.factories import OrderFactory, OrderItemFactory, ProductFactory
from account.factories import UserFactory
from orders.models import Order

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(api_client):
    user_obj = UserFactory()
    api_client.force_authenticate(user=user_obj)
    return user_obj


@pytest.fixture
def product():
    return ProductFactory(stock=20, price=Decimal('50.00'))


@pytest.fixture
def order(user, product):
    order_obj = OrderFactory(user=user, status='PENDING', payment_status='PENDING')
    OrderItemFactory(order=order_obj, product=product, quantity=2, price=product.price)
    order_obj.calculate_total_payable()
    order_obj.save()
    return order_obj


class TestPaymentAPIViews:

    @patch('payment.gateways.ZibalGateway.create_payment_request')
    def test_payment_process_success(self, mock_create_request, api_client, user, order):
        mock_create_request.return_value = {
            'trackId': '12345',
            'paymentUrl': 'https://gateway.zibal.ir/start/12345'
        }

        url = reverse('api-v1:payment:process')
        data = {'order_id': str(order.order_id)}
        response = api_client.post(url, data)

        order.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert response.data['payment_url'] == 'https://gateway.zibal.ir/start/12345'
        assert order.payment_track_id == '12345'

    @patch('payment.gateways.ZibalGateway.verify_payment')
    def test_payment_verify_success(self, mock_verify, api_client, user, order):
        order.payment_track_id = '12345'
        order.save()

        mock_verify.return_value = {'status': 'SUCCESS', 'refNumber': 'ABC-123'}

        url = reverse('api-v1:payment:verify')
        params = {'trackId': '12345'}
        response = api_client.get(url, params)

        order.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert order.status == 'PAID'
        assert order.payment_status == 'SUCCESS'
        assert order.payment_ref_id == 'ABC-123'

        order.items.first().product.refresh_from_db()
        assert order.items.first().product.stock == 18

    @patch('payment.gateways.ZibalGateway.verify_payment')
    def test_payment_verify_failed(self, mock_verify, api_client, user, order):
        order.payment_track_id = '67890'
        order.save()

        mock_verify.return_value = {'status': 'FAILED'}

        url = reverse('api-v1:payment:verify')
        params = {'trackId': '67890'}
        response = api_client.get(url, params)

        order.refresh_from_db()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'failed'
        assert order.status == 'PENDING'
        assert order.payment_status == 'FAILED'

        order.items.first().product.refresh_from_db()
        assert order.items.first().product.stock == 20

    def test_cannot_process_paid_order(self, api_client, user, order):
        order.status = 'PAID'
        order.save()

        url = reverse('api-v1:payment:process')
        data = {'order_id': str(order.order_id)}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already been paid' in response.data['detail']
