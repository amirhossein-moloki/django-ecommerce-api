from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from sms.models import OTPCode

User = get_user_model()


class UserViewSetTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+989123456789',
            username='testuser',
            password='S@mpleP@ss123',
            is_active=True
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('auth:current_user')

    def test_get_user_profile(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['username'], self.user.username)

    def test_update_user_profile(self):
        data = {
            'first_name': 'Updated',
            'password': 'S@mpleP@ss123'
        }
        response = self.client.put(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')

    def test_patch_user_profile(self):
        data = {
            'first_name': 'Patched',
            'password': 'S@mpleP@ss123'
        }
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Patched')

    def test_delete_user_profile(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_staff_check(self):
        url = reverse('auth:staff_check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_staff'])

        self.user.is_staff = True
        self.user.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_staff'])






class OTPTests(APITestCase):

    @patch('sms.providers.SmsIrProvider.send_otp')
    def test_request_otp_success(self, mock_send_otp):
        mock_send_otp.return_value = {'status': 1}
        url = reverse('auth:request-otp')
        data = {'phone': '+989123456789'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTPCode.objects.filter(phone='+989123456789', is_active=True).exists())

    def test_verify_otp_new_user(self):
        expires_at = timezone.now() + timedelta(minutes=2)
        OTPCode.objects.create(phone='+989123456789', code='123456', expires_at=expires_at)
        url = reverse('auth:verify-otp')
        data = {'phone': '+989123456789', 'code': '123456'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertFalse(response.data['is_profile_complete'])
        user = User.objects.get(phone_number='+989123456789')
        self.assertFalse(user.is_profile_complete)
        self.assertFalse(user.is_active)

    def test_verify_otp_existing_user(self):
        User.objects.create_user(
            phone_number="+989123456789", username="test", is_profile_complete=True
        )
        expires_at = timezone.now() + timedelta(minutes=2)
        OTPCode.objects.create(phone='+989123456789', code='123456', expires_at=expires_at)
        url = reverse('auth:verify-otp')
        data = {'phone': '+989123456789', 'code': '123456'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_profile_complete'])

    def test_verify_otp_invalid_code(self):
        expires_at = timezone.now() + timedelta(minutes=2)
        OTPCode.objects.create(phone='+989123456789', code='123456', expires_at=expires_at)
        url = reverse('auth:verify-otp')
        data = {'phone': '+989123456789', 'code': '654321'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_otp_expired_code(self):
        expires_at = timezone.now() - timedelta(minutes=1)
        OTPCode.objects.create(phone='+989123456789', code='123456', expires_at=expires_at)
        url = reverse('auth:verify-otp')
        data = {'phone': '+989123456789', 'code': '123456'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CompleteProfileViewTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+989123456789',
            username='testuser',
            password='S@mpleP@ss123',
            is_active=False,
            is_profile_complete=False
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('auth:complete-profile')

    def test_complete_profile_success(self):
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com'
        }
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_profile_complete)
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.first_name, 'Test')

    def test_complete_profile_already_complete(self):
        self.user.is_profile_complete = True
        self.user.save()
        data = {'first_name': 'Another Name'}
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
