from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from sms.models import OTPCode

User = get_user_model()


@pytest.mark.django_db
@patch("sms.views.SmsIrProvider.send_otp")
def test_request_otp_valid_phone(mock_send_otp):
    client = APIClient()
    url = reverse("sms:request-otp")
    phone = "09123456789"

    response = client.post(url, {"phone": phone})

    assert response.status_code == status.HTTP_200_OK
    assert OTPCode.objects.filter(phone=phone).exists()
    mock_send_otp.assert_called_once()


@pytest.mark.django_db
@patch("sms.views.SmsIrProvider.send_otp")
def test_request_otp_invalid_phone(mock_send_otp):
    client = APIClient()
    url = reverse("sms:request-otp")

    response = client.post(url, {})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert OTPCode.objects.count() == 0
    mock_send_otp.assert_not_called()


@pytest.mark.django_db
def test_verify_otp_valid_creates_user():
    client = APIClient()
    url = reverse("sms:verify-otp")
    phone = "09120000000"
    OTPCode.objects.create(
        phone=phone,
        code="123456",
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
    )

    response = client.post(url, {"phone": phone, "code": "123456"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["data"]["access"]
    assert response.data["data"]["refresh"]
    assert User.objects.filter(phone_number=phone).exists()
    otp = OTPCode.objects.get(phone=phone, code="123456")
    assert otp.used is True


@pytest.mark.django_db
def test_verify_otp_invalid_code():
    client = APIClient()
    url = reverse("sms:verify-otp")
    phone = "09121111111"
    OTPCode.objects.create(
        phone=phone,
        code="123456",
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
    )

    response = client.post(url, {"phone": phone, "code": "654321"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "Invalid or expired OTP"


@pytest.mark.django_db
def test_verify_otp_expired_code():
    client = APIClient()
    url = reverse("sms:verify-otp")
    phone = "09122222222"
    OTPCode.objects.create(
        phone=phone,
        code="123456",
        expires_at=timezone.now() - timezone.timedelta(minutes=5),
    )

    response = client.post(url, {"phone": phone, "code": "123456"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "Invalid or expired OTP"
