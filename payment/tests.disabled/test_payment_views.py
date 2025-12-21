import pytest
from unittest.mock import patch
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from orders.factories import OrderFactory
from orders.models import Order
from payment.models import PaymentTransaction

pytestmark = pytest.mark.django_db


@patch('payment.gateways.ZibalGateway.create_payment_request')
def test_payment_process_success(mock_create_request, api_client, user):
    mock_create_request.return_value = {
        'trackId': '12345',
        'paymentUrl': 'https://gateway.zibal.ir/start/12345'
    }
    order = OrderFactory.create(user=user)
    url = reverse('payment:process', kwargs={'order_id': order.order_id})
    response = api_client.post(url)
    order.refresh_from_db()
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['payment_url'] == 'https://gateway.zibal.ir/start/12345'
    assert order.payment_track_id == '12345'


@patch('payment.services.create_postex_shipment_task.delay')
@patch('payment.gateways.ZibalGateway.verify_payment')
def test_payment_verify_success(mock_verify, mock_create_shipment, api_client, user):
    order = OrderFactory.create(user=user, total_payable=Decimal('100.00'), payment_track_id='12345')
    mock_verify.return_value = {
        'result': 100,
        'refNumber': 'ABC-123',
        'amount': int(order.total_payable * 10),
        'orderId': str(order.order_id),
    }
    url = reverse('payment:verify')
    params = {'trackId': '12345', 'success': '1'}
    response = api_client.get(url, params)
    order.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert response.data['status'] == 'success'
    assert order.status == Order.Status.PAID
    assert order.payment_status == Order.PaymentStatus.SUCCESS
    assert order.payment_ref_id == 'ABC-123'
    assert PaymentTransaction.objects.filter(track_id='12345').exists()
