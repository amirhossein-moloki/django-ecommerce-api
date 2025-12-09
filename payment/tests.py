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


class PaymentGatewayTests(TestCase):
    @patch('payment.gateways.requests.post')
    def test_zibal_create_payment_request(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'result': 100, 'trackId': '12345'}
        from payment.gateways import ZibalGateway
        gateway = ZibalGateway()
        response = gateway.create_payment_request(1000, 'test-order', 'http://test.com/callback')
        self.assertEqual(response['result'], 100)

    @patch('payment.gateways.requests.post')
    def test_zibal_verify_payment(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'result': 100}
        from payment.gateways import ZibalGateway
        gateway = ZibalGateway()
        response = gateway.verify_payment('12345')
        self.assertEqual(response['result'], 100)


class PaymentAPIViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+989123456717',
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
        self.process_url = reverse('payment:process', kwargs={'order_id': self.order.order_id})
        self.verify_url = reverse('payment:verify')

    @patch('payment.services.ZibalGateway.create_payment_request')
    def test_process_payment(self, mock_create_request):
        mock_create_request.return_value = {'result': 100, 'trackId': '12345'}
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.process_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('payment.services.ZibalGateway.verify_payment')
    @patch('payment.services.create_postex_shipment_task.delay')
    def test_verify_payment(self, mock_create_shipment, mock_verify):
        mock_verify.return_value = {'result': 100}
        self.order.payment_track_id = '12345'
        self.order.save()
        response = self.client.get(self.verify_url + '?trackId=12345')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PaymentWebhookAPIViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+989123456718',
            email='testwebhook@example.com',
            username='testwebhookuser',
            password='password'
        )
        self.order = Order.objects.create(user=self.user, total_payable=Decimal('250.00'), payment_track_id='track123')
        self.webhook_url = reverse('payment:webhook')

    @patch('payment.views.process_successful_payment.delay')
    def test_webhook_success(self, mock_task):
        """
        Test a successful webhook call.
        """
        payload = {'trackId': 'track123', 'success': True}
        headers = {'X-Zibal-Secret': 'your-super-secret-webhook-key'}
        response = self.client.post(self.webhook_url, payload, format='json', **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_task.assert_called_once_with('track123', True)

    def test_webhook_invalid_secret(self):
        """
        Test a webhook call with an invalid secret.
        """
        payload = {'trackId': 'track123', 'success': True}
        headers = {'X-Zibal-Secret': 'invalid-secret'}
        response = self.client.post(self.webhook_url, payload, format='json', **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('payment.views.process_successful_payment.delay')
    def test_webhook_idempotency(self, mock_task):
        """
        Test that a successful webhook is not processed twice.
        """
        # First successful call
        payload = {'trackId': 'track123', 'success': True}
        headers = {'X-Zibal-Secret': 'your-super-secret-webhook-key'}
        response = self.client.post(self.webhook_url, payload, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_task.assert_called_once_with('track123', True)

        # Mark the order as successful
        self.order.payment_status = Order.PaymentStatus.SUCCESS
        self.order.save()

        # Second call should not trigger the task again
        mock_task.reset_mock()
        response = self.client.post(self.webhook_url, payload, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Webhook already processed.')
        mock_task.assert_not_called()
