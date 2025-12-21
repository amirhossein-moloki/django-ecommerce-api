import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.factories import UserFactory
from coupons.factories import CouponFactory

pytestmark = pytest.mark.django_db


class TestCouponApi:
    def setup_class(self):
        self.client = APIClient()
        self.apply_coupon_url = reverse("api-v1:coupon-apply-coupon")

    def test_apply_coupon_requires_authentication(self):
        """
        Tests that an unauthenticated user cannot apply a coupon.
        """
        coupon = CouponFactory(active=True)
        data = {"code": coupon.code}
        response = self.client.post(self.apply_coupon_url, data)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_apply_coupon_user_rate_limit(self):
        """
        Tests that the user-based rate limit is enforced for applying coupons.
        """
        user = UserFactory()
        self.client.force_authenticate(user=user)
        coupon = CouponFactory(active=True)
        data = {"code": coupon.code}

        # Exhaust the rate limit (5 requests per minute)
        for i in range(5):
            response = self.client.post(self.apply_coupon_url, data)
            assert response.status_code == status.HTTP_200_OK

        # The 6th request should be rate-limited
        response = self.client.post(self.apply_coupon_url, data)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_apply_coupon_ip_rate_limit(self):
        """
        Tests that the IP-based rate limit is enforced across multiple users.
        """
        coupon = CouponFactory(active=True)
        data = {"code": coupon.code}
        ip_address = "127.0.0.1"

        # User 1 makes 5 requests, should be successful
        user1 = UserFactory()
        self.client.force_authenticate(user=user1)
        for _ in range(5):
            response = self.client.post(self.apply_coupon_url, data, REMOTE_ADDR=ip_address)
            assert response.status_code == status.HTTP_200_OK

        # User 2 makes 5 requests from the same IP, should also be successful
        # This brings the total for the IP to 10
        user2 = UserFactory()
        self.client.force_authenticate(user=user2)
        for _ in range(5):
            response = self.client.post(self.apply_coupon_url, data, REMOTE_ADDR=ip_address)
            assert response.status_code == status.HTTP_200_OK

        # The 11th request from the same IP (using user1) should be rate-limited
        self.client.force_authenticate(user=user1)
        response = self.client.post(self.apply_coupon_url, data, REMOTE_ADDR=ip_address)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
