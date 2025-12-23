import pytest
from unittest.mock import patch
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from .models import Order, OrderItem
from .factories import OrderFactory
from account.factories import UserFactory, AddressFactory
from shop.factories import ProductVariantFactory
from coupons.factories import CouponFactory

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(transaction=True)
class TestOrderServices:
    def test_get_user_orders(self, api_client):
        user1 = UserFactory()
        user2 = UserFactory()
        staff_user = UserFactory(is_staff=True)
        order1 = OrderFactory(user=user1)
        OrderFactory(user=user2)
        api_client.force_authenticate(user=user1)
        response = api_client.get(reverse('api-v1:order-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['order_id'] == str(order1.order_id)
        api_client.force_authenticate(user=staff_user)
        response = api_client.get(reverse('api-v1:order-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    @patch('orders.services.send_order_confirmation_email.delay')
    def test_create_order_success(self, mock_send_email, api_client):
        user = UserFactory()
        address = AddressFactory(user=user)
        variant = ProductVariantFactory(stock=10)
        api_client.force_authenticate(user=user)
        cart_add_url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(cart_add_url, {'quantity': 2}, format='json')
        order_create_url = reverse('api-v1:order-list')
        response = api_client.post(order_create_url, {'address_id': address.id}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Order.objects.count() == 1
        order = Order.objects.first()
        variant.refresh_from_db()
        assert variant.stock == 8
        mock_send_email.assert_called_once_with(order.order_id)

    def test_create_order_insufficient_stock(self, api_client):
        user = UserFactory()
        address = AddressFactory(user=user)
        variant = ProductVariantFactory(stock=1)
        api_client.force_authenticate(user=user)
        cart_add_url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(cart_add_url, {'quantity': 2}, format='json')
        order_create_url = reverse('api-v1:order-list')
        response = api_client.post(order_create_url, {'address_id': address.id}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'stock' in str(response.data).lower()
        variant.refresh_from_db()
        assert variant.stock == 1
        assert Order.objects.count() == 0

    def test_price_is_snapshotted(self, api_client):
        user = UserFactory()
        address = AddressFactory(user=user)
        variant = ProductVariantFactory(price=Decimal('100.00'))
        api_client.force_authenticate(user=user)
        cart_add_url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(cart_add_url, {'quantity': 1}, format='json')
        order_create_url = reverse('api-v1:order-list')
        response = api_client.post(order_create_url, {'address_id': address.id}, format='json')
        order_id = response.data['order_id']
        order_item = OrderItem.objects.get(order__order_id=order_id)
        assert order_item.price == Decimal('100.00')
        variant.price = Decimal('150.00')
        variant.save()
        order_item.refresh_from_db()
        assert order_item.price == Decimal('100.00')

    def test_apply_valid_coupon(self, api_client):
        user = UserFactory()
        address = AddressFactory(user=user)
        variant = ProductVariantFactory(price=Decimal('100.00'), stock=10)
        coupon = CouponFactory(discount=20)
        api_client.force_authenticate(user=user)
        cart_add_url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(cart_add_url, {'quantity': 2}, format='json')
        order_create_url = reverse('api-v1:order-list')
        response = api_client.post(order_create_url, {'address_id': address.id, 'coupon_code': coupon.code}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        order = Order.objects.first()
        assert order.coupon == coupon
        assert order.discount_amount == Decimal('40.00')
        assert order.total_payable == Decimal('160.00')

    def test_apply_invalid_coupon(self, api_client):
        user = UserFactory()
        address = AddressFactory(user=user)
        variant = ProductVariantFactory(price=Decimal('100.00'), stock=10)
        api_client.force_authenticate(user=user)
        cart_add_url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(cart_add_url, {'quantity': 2}, format='json')
        order_create_url = reverse('api-v1:order-list')
        response = api_client.post(order_create_url, {'address_id': address.id, 'coupon_code': 'INVALIDCODE'}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'coupon' in str(response.data).lower()
        assert Order.objects.count() == 0

    def test_invalid_address_id(self, api_client):
        user = UserFactory()
        variant = ProductVariantFactory(stock=10)
        api_client.force_authenticate(user=user)
        cart_add_url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(cart_add_url, {'quantity': 1}, format='json')
        order_create_url = reverse('api-v1:order-list')
        response = api_client.post(order_create_url, {'address_id': 9999}, format='json') # Non-existent address ID
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'address' in str(response.data).lower()
        assert Order.objects.count() == 0
