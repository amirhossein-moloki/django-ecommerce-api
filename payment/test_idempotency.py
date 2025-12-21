import uuid
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from account.models import UserAccount
from orders.models import Order, OrderItem
from shop.models import Product


class PaymentIdempotencyTests(APITestCase):

    def setUp(self):
        self.user = UserAccount.objects.create_user(email='testuser@example.com', password='password')
        self.product = Product.objects.create(
            name='Test Product',
            price=10000,
            stock=10,
            weight=1,
            length=1,
            width=1,
            height=1,
        )
        self.order = Order.objects.create(user=self.user, total_payable=10000)
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price=10000)
        self.track_id = str(uuid.uuid4())
        self.order.payment_track_id = self.track_id
        self.order.save()

    @patch('payment.gateways.ZibalGateway.verify_payment')
    def test_replay_attack_is_prevented(self, mock_verify_payment):
        """
        Ensure that processing the same successful verification multiple times
        does not result in multiple successful payments for the same order.
        """
        # Mock the Zibal gateway to return a successful verification
        mock_verify_payment.return_value = {
            'result': 100,  # Success
            'amount': int(self.order.total_payable * 10),
            'orderId': str(self.order.order_id),
            'refNumber': 'mock-ref-number'
        }

        # Simulate the first successful verification
        url = f"{reverse('payment:verify')}?trackId={self.track_id}&success=1"
        response = self.client.get(url)

        # Check that the first verification was successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.SUCCESS)

        # Simulate a replay attack by sending the same verification request again
        response_replay = self.client.get(url)

        # Check that the replay attempt was also successful, but did not re-process the payment
        self.assertEqual(response_replay.status_code, status.HTTP_200_OK)
        self.assertIn("already been successfully verified", response_replay.data['message'])

        # Assert that the Zibal gateway's verify_payment method was only called once
        self.assertEqual(mock_verify_payment.call_count, 1)
