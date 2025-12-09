from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import OTPCode
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class OTPCodeModelTests(TestCase):
    def test_is_expired(self):
        otp = OTPCode.objects.create(
            phone="123", code="123456", expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertTrue(otp.is_expired())


class SmsProviderTests(TestCase):
    @patch("sms.providers.requests.post")
    def test_smsir_send_otp(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "success"}
        from .providers import SmsIrProvider

        provider = SmsIrProvider()
        response = provider.send_otp("123", "123456", 1)
        self.assertEqual(response["status"], "success")

    @patch("sms.providers.requests.post")
    def test_smsir_send_text(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "success"}
        from .providers import SmsIrProvider

        provider = SmsIrProvider()
        response = provider.send_text("123", "test message")
        self.assertEqual(response["status"], "success")


class SMSAPIViewTests(APITestCase):
    @patch("sms.views.SmsIrProvider.send_otp")
    def test_request_otp(self, mock_send_otp):
        mock_send_otp.return_value = {"status": "success"}
        url = reverse("sms:request-otp")
        data = {"phone": "123"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_otp(self):
        OTPCode.objects.create(
            phone="123", code="123456", expires_at=timezone.now() + timedelta(minutes=5)
        )
        url = reverse("sms:verify-otp")
        data = {"phone": "123", "code": "123456"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
