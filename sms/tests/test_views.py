
import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from ..models import OTPCode
from django.test import override_settings

pytestmark = pytest.mark.django_db


class TestRequestOTPAPI:
    @patch('sms.views.SmsIrProvider.send_otp')
    def test_request_otp_success(self, mock_send_otp, api_client):
        url = reverse('sms:request-otp')
        phone_number = "09123456789"
        data = {'phone': phone_number}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True
        assert response.json()['message'] == "OTP sent successfully"
        assert OTPCode.objects.filter(phone=phone_number).exists()
        mock_send_otp.assert_called_once()

    def test_request_otp_missing_phone(self, api_client):
        url = reverse('sms:request-otp')
        data = {}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()['success'] is False
        assert "Phone number is required" in response.json()['message']

    # This test requires the django-ratelimit library to be configured with a cache
    # that persists across requests in a test, like the default locmem cache.
    @override_settings(
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'unique-snowflake',
            }
        },
        RATELIMIT_USE_CACHE='default'
    )
    @patch('sms.views.SmsIrProvider.send_otp')
    def test_request_otp_rate_limit(self, mock_send_otp, api_client):
        url = reverse('sms:request-otp')
        phone_number = "09123456788"
        data = {'phone': phone_number}

        # The rate is 3/m. First 3 requests should succeed.
        for i in range(3):
            response = api_client.post(url, data)
            assert response.status_code == status.HTTP_200_OK, f"Request {i+1} failed"

        # The 4th request should be blocked.
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Ensure the provider was only called 3 times.
        assert mock_send_otp.call_count == 3
