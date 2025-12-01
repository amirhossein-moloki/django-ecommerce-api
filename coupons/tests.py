from datetime import timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from coupons.models import Coupon
from django.urls import reverse

User = get_user_model()


class CouponModelTests(TestCase):
    def test_clean_invalid_dates(self):
        coupon = Coupon(
            code='INVALID',
            valid_from=timezone.now(),
            valid_to=timezone.now() - timedelta(days=1),
            discount=10
        )
        with self.assertRaises(ValidationError):
            coupon.clean()

    def test_is_valid(self):
        valid_coupon = Coupon.objects.create(
            code='VALID',
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=1),
            discount=10,
            active=True
        )
        invalid_coupon = Coupon.objects.create(
            code='INVALID',
            valid_from=timezone.now() - timedelta(days=2),
            valid_to=timezone.now() - timedelta(days=1),
            discount=10,
            active=True
        )
        self.assertTrue(valid_coupon.is_valid())
        self.assertFalse(invalid_coupon.is_valid())

    def test_increment_usage_count(self):
        coupon = Coupon.objects.create(
            code='TEST',
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=1),
            discount=10
        )
        coupon.increment_usage_count()
        coupon.refresh_from_db()
        self.assertEqual(coupon.usage_count, 1)


class CouponViewSetTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            username='staff',
            password='password',
            is_staff=True
        )
        self.coupon = Coupon.objects.create(
            code='TESTCOUPON',
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=1),
            discount=10
        )
        self.apply_url = reverse('api-v1:coupon-apply-coupon')
        self.detail_url = reverse('api-v1:coupon-detail', kwargs={'pk': self.coupon.pk})

    def test_apply_coupon(self):
        self.client.force_authenticate(user=self.staff_user)
        data = {'code': self.coupon.code}
        response = self.client.post(self.apply_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_coupon(self):
        self.client.force_authenticate(user=self.staff_user)
        data = {'discount': 20}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.discount, 20)

    def test_update_coupon_code_not_allowed(self):
        self.client.force_authenticate(user=self.staff_user)
        data = {'code': 'NEWCODE'}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_destroy_coupon(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.coupon.refresh_from_db()
        self.assertFalse(self.coupon.active)
