from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from djoser.utils import encode_uid
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from datetime import timedelta

from sms.models import OTPCode

User = get_user_model()


class UserViewSetTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
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


class AuthenticationTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='S@mpleP@ss123',
            is_active=False
        )
        self.uid = encode_uid(self.user.pk)
        self.token = default_token_generator.make_token(self.user)

    def test_user_registration(self):
        url = reverse('auth:register')
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'S@mpleP@ss123',
            're_password': 'S@mpleP@ss123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_user_activation(self):
        url = reverse('auth:activate')
        data = {'uid': self.uid, 'token': self.token}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_set_password(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('auth:set_password')
        data = {
            'new_password': 'NewS@mpleP@ss123',
            'current_password': 'S@mpleP@ss123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewS@mpleP@ss123'))

    def test_reset_password(self):
        self.user.is_active = True
        self.user.save()
        url = reverse('auth:reset_password')
        data = {'email': self.user.email}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_reset_password_confirm(self):
        url = reverse('auth:reset_password_confirm')
        data = {
            'uid': self.uid,
            'token': self.token,
            'new_password': 'NewPassword123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_token_obtain(self):
        self.user.is_active = True
        self.user.save()
        url = reverse('auth:jwt-create')
        data = {'email': self.user.email, 'password': 'S@mpleP@ss123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])

    def test_token_refresh(self):
        self.user.is_active = True
        self.user.save()
        refresh = RefreshToken.for_user(self.user)
        url = reverse('auth:jwt-refresh')
        data = {'refresh': str(refresh)}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])

    def test_token_verify(self):
        self.user.is_active = True
        self.user.save()
        refresh = RefreshToken.for_user(self.user)
        url = reverse('auth:jwt-verify')
        data = {'token': str(refresh.access_token)}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_destroy(self):
        self.user.is_active = True
        self.user.save()
        refresh = RefreshToken.for_user(self.user)
        url = reverse('auth:jwt-destroy')
        data = {'refresh': str(refresh)}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)


class ActivateViewTest(APITestCase):
    def test_activate_view(self):
        url = reverse('auth:activate-form', kwargs={'uid': 'test_uid', 'token': 'test_token'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'account/activate.html')


class OTPTests(APITestCase):

    @patch('sms.providers.SmsIrProvider.send_otp')
    def test_request_otp(self, mock_send_otp):
        mock_send_otp.return_value = {'status': 1}
        url = reverse('auth:request-otp')
        data = {'phone': '+989123456789'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(OTPCode.objects.filter(phone='+989123456789').exists())

    def test_verify_otp(self):
        expires_at = timezone.now() + timedelta(minutes=5)
        otp = OTPCode.objects.create(phone='+989123456789', code='123456', expires_at=expires_at)
        url = reverse('auth:verify-otp')
        data = {'phone': '+989123456789', 'code': '123456'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        user = User.objects.get(phone_number='+989123456789')
        self.assertIsNotNone(user)
        otp.refresh_from_db()
        self.assertTrue(otp.used)
