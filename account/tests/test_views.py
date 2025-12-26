from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from account.models import UserAccount, Profile
from sms.models import OTPCode


class TestAccountViews(APITestCase):
    def setUp(self):
        self.request_otp_url = reverse("auth:request-otp")
        self.verify_otp_url = reverse("auth:verify-otp")
        self.complete_profile_url = reverse("auth:complete-profile")
        self.me_url = reverse("auth:current_user")
        self.logout_url = reverse("auth:jwt-destroy")

        self.user_phone = "+989123456789"
        self.user_data = {
            "phone_number": self.user_phone,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "strongpassword123",
        }
        self.user = UserAccount.objects.create_user(
            **self.user_data, is_profile_complete=True
        )

    @patch("sms.providers.SmsIrProvider.send_otp")
    def test_request_otp_success(self, mock_send_otp):
        mock_send_otp.return_value = {"status": 1}
        response = self.client.post(self.request_otp_url, {"phone": self.user_phone})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTPCode.objects.filter(phone=self.user_phone).exists())

    def test_request_otp_no_phone(self):
        response = self.client.post(self.request_otp_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_otp_success_existing_user_login(self):
        otp = OTPCode.objects.create(
            phone=self.user_phone,
            code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=2),
        )
        response = self.client.post(
            self.verify_otp_url, {"phone": self.user_phone, "code": "123456"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(response.data["is_profile_complete"])

    def test_verify_otp_success_new_user_signup(self):
        new_phone = "+989120000000"
        otp = OTPCode.objects.create(
            phone=new_phone,
            code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=2),
        )
        response = self.client.post(
            self.verify_otp_url, {"phone": new_phone, "code": "123456"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertFalse(response.data["is_profile_complete"])
        self.assertTrue(UserAccount.objects.filter(phone_number=new_phone).exists())

    def test_verify_otp_invalid_code(self):
        OTPCode.objects.create(
            phone=self.user_phone,
            code="123456",
            expires_at=timezone.now() + timezone.timedelta(minutes=2),
        )
        response = self.client.post(
            self.verify_otp_url, {"phone": self.user_phone, "code": "654321"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid OTP", str(response.content))

    def test_verify_otp_expired_code(self):
        otp = OTPCode.objects.create(
            phone=self.user_phone,
            code="123456",
            expires_at=timezone.now() - timezone.timedelta(minutes=5),
        )
        response = self.client.post(
            self.verify_otp_url, {"phone": self.user_phone, "code": "123456"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("OTP has expired", str(response.content))

    def test_get_me_authenticated(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["phone_number"], self.user_phone)
        self.assertNotIn("password", response.data["data"])

    def test_get_me_unauthenticated(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_complete_profile_success(self):
        new_user = UserAccount.objects.create_user(
            phone_number="+989121111111",
            username="+989121111111",
            password="password",
            is_profile_complete=False,
        )
        refresh = RefreshToken.for_user(new_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        profile_data = {
            "username": "newusername",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.patch(self.complete_profile_url, profile_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_user.refresh_from_db()
        self.assertTrue(new_user.is_profile_complete)
        self.assertEqual(new_user.username, "newusername")

    def test_complete_profile_already_complete(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        profile_data = {"username": "anotherusername"}
        response = self.client.patch(self.complete_profile_url, profile_data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_success(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = self.client.post(self.logout_url, {"refresh": str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

    def test_logout_invalid_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = self.client.post(self.logout_url, {"refresh": "invalidtoken"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
