import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from coupons.factories import CouponFactory
from shop.factories import ProductFactory
from account.factories import UserFactory
from cart.cart import Cart

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(api_client):
    user_obj = UserFactory()
    api_client.force_authenticate(user=user_obj)
    return user_obj


@pytest.fixture
def cart(api_client, user):
    # The cart needs a request object, which the client can provide
    request = type('Request', (), {'session': api_client.session, 'user': user})
    cart_instance = Cart(request)
    product = ProductFactory(stock=10)
    cart_instance.add(product, 1)
    return cart_instance


class TestCouponViewSetApplyAction:

    def test_apply_valid_coupon_successfully(self, api_client, user, cart):
        coupon = CouponFactory()
        url = reverse('api-v1:coupons-apply')
        data = {'code': coupon.code}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['detail'] == 'Coupon applied successfully.'
        assert api_client.session['coupon_id'] == coupon.id

    def test_apply_invalid_coupon_code_fails(self, api_client, user, cart):
        url = reverse('api-v1:coupons-apply')
        data = {'code': 'INVALIDCODE'}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'coupon_id' not in api_client.session

    def test_apply_expired_coupon_fails(self, api_client, user, cart):
        coupon = CouponFactory(valid_to=timezone.now() - timedelta(days=1))
        url = reverse('api-v1:coupons-apply')
        data = {'code': coupon.code}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'coupon_id' not in api_client.session

    def test_apply_inactive_coupon_fails(self, api_client, user, cart):
        coupon = CouponFactory(is_active=False)
        url = reverse('api-v1:coupons-apply')
        data = {'code': coupon.code}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'coupon_id' not in api_client.session

    def test_apply_coupon_with_full_usage_fails(self, api_client, user, cart):
        coupon = CouponFactory(max_usage_count=1, usage_count=1)
        url = reverse('api-v1:coupons-apply')
        data = {'code': coupon.code}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'coupon_id' not in api_client.session
