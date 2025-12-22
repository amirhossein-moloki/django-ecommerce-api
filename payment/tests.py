import pytest
from unittest.mock import patch
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from orders.factories import OrderFactory
from account.factories import UserFactory, AddressFactory

pytestmark = pytest.mark.django_db


class TestPaymentAPI:
    @patch('payment.gateways.ZibalGateway.create_payment_request')
    def test_process_payment(self, mock_create_request, api_client, user):
        mock_create_request.return_value = {'result': 100, 'trackId': '12345'}
        api_client.force_authenticate(user=user)
        order = OrderFactory.create(user=user, total_payable=Decimal('100.00'))
        url = reverse('payment:process', kwargs={'order_id': order.order_id})
        response = api_client.post(url)
        assert response.status_code == status.HTTP_201_CREATED

    @patch('payment.services.create_postex_shipment_task.delay')
    @patch('payment.gateways.ZibalGateway.verify_payment')
    def test_verify_payment(self, mock_verify, mock_create_shipment, api_client, user):
        order = OrderFactory.create(user=user, total_payable=Decimal('100.00'), payment_track_id='12345')
        mock_verify.return_value = {
            'result': 100,
            'amount': int(order.total_payable * 10),
            'orderId': str(order.order_id),
        }
        url = reverse('payment:verify')
        params = {'trackId': '12345', 'success': '1'}
        response = api_client.get(url, params)
        assert response.status_code == status.HTTP_200_OK
