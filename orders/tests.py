import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from shop.factories import ProductFactory, UserFactory
from coupons.factories import CouponFactory
from account.factories import AddressFactory
from .factories import OrderFactory, OrderItemFactory
from .models import Order, OrderItem
from shop.models import Product

pytestmark = pytest.mark.django_db


class TestOrderModel:
    def test_get_total_cost(self):
        order = OrderFactory()
        p1 = ProductFactory(price='10.00')
        p2 = ProductFactory(price='20.00')
        v1 = p1.variants.first()
        v2 = p2.variants.first()
        OrderItemFactory(order=order, variant=v1, quantity=1, price=v1.price)
        OrderItemFactory(order=order, variant=v2, quantity=2, price=v2.price)
        assert order.get_total_cost_before_discount() == Decimal('50.00')

    def test_get_discount(self):
        coupon = CouponFactory(discount=10)
        order = OrderFactory(coupon=coupon)
        p1 = ProductFactory(price='10.00')
        v1 = p1.variants.first()
        OrderItemFactory(order=order, variant=v1, quantity=1, price=v1.price)
        assert order.get_discount() == Decimal('1.00')


class TestOrderAPI:
    def test_create_order(self, api_client, user):
        api_client.force_authenticate(user=user)
        address = AddressFactory(user=user)
        product = ProductFactory(stock=10)
        variant = product.variants.first()

        # Add to cart
        url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(url, {'quantity': 1}, format='json')

        # Create order
        url = reverse('api-v1:order-list')
        data = {'address_id': address.id}
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert Order.objects.count() == 1
        variant.refresh_from_db()
        assert variant.stock == 9

    def test_overselling_prevention(self, api_client, user):
        api_client.force_authenticate(user=user)
        address = AddressFactory(user=user)
        product = ProductFactory(stock=1)
        variant = product.variants.first()

        # Add to cart
        url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(url, {'quantity': 1}, format='json')

        # Create order - should succeed
        url = reverse('api-v1:order-list')
        data = {'address_id': address.id}
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        # Try to create another order with the same out-of-stock item
        api_client.post(url, data, format='json')
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPriceSnapshot:
    def test_price_is_snapshotted(self, api_client, user):
        api_client.force_authenticate(user=user)
        address = AddressFactory(user=user)
        product = ProductFactory(price='100.00')
        variant = product.variants.first()

        # Add to cart and create order
        url = reverse('api-v1:cart-add', kwargs={'variant_id': variant.variant_id})
        api_client.post(url, {'quantity': 1}, format='json')
        url = reverse('api-v1:order-list')
        data = {'address_id': address.id}
        response = api_client.post(url, data, format='json')
        order_id = response.data['order_id']

        # Verify initial price
        order_item = OrderItem.objects.get(order__order_id=order_id)
        assert order_item.price == Decimal('100.00')

        # Change product price
        variant.price = Decimal('150.00')
        variant.save()

        # Verify order item price has not changed
        order_item.refresh_from_db()
        assert order_item.price == Decimal('100.00')
