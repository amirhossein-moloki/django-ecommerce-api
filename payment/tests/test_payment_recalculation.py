import pytest
from unittest.mock import patch
from decimal import Decimal
from django.utils import timezone
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.request import Request as DRFRequest

from account.factories import UserFactory
from coupons.factories import CouponFactory
from orders.factories import OrderFactory, OrderItemFactory
from shop.factories import ProductFactory
from payment.services import process_payment


@pytest.mark.django_db
class TestPaymentRecalculation:
    """
    Test suite for ensuring order amounts and conditions are re-validated
    and recalculated atomically before processing a payment.
    """

    def setup_method(self):
        """Set up common test data."""
        self.user = UserFactory()
        self.product = ProductFactory(price=Decimal("100.00"), stock=10)
        self.order = OrderFactory(user=self.user, coupon=None)
        self.order_item = OrderItemFactory(
            order=self.order, product=self.product, quantity=2, price=self.product.price
        )
        self.order.calculate_total_payable()
        self.order.save()
        # Use Django's RequestFactory and wrap it in DRF's Request
        http_request = RequestFactory().post(
            reverse('payment:process', kwargs={'order_id': self.order.order_id})
        )
        http_request.user = self.user
        self.drf_request = DRFRequest(http_request)

    @patch('payment.services.ZibalGateway.create_payment_request')
    def test_recalculation_on_product_price_change(self, mock_create_request):
        """
        Verify that if a product's price changes, the order total is recalculated
        to the new price before payment.
        """
        mock_create_request.return_value = {'trackId': 'zibal-12345', 'result': 100}

        # Price increases from 100 to 120 after order creation
        self.product.price = Decimal("120.00")
        self.product.save()

        # Execute the payment process
        process_payment(self.drf_request, self.order.order_id)

        self.order.refresh_from_db()

        # Assert that the order totals were updated to reflect the new price
        assert self.order.subtotal == Decimal("240.00")  # 2 * 120.00
        assert self.order.total_payable == Decimal("240.00")

        # Assert the gateway was called with the RECALCULATED amount
        mock_create_request.assert_called_once()
        called_kwargs = mock_create_request.call_args.kwargs
        assert called_kwargs['amount'] == 24000  # 240.00 Toman * 100 = 24000 Rials

    def test_payment_fails_if_coupon_expires(self):
        """
        Verify payment fails if a coupon's validity date expires between
        order creation and payment.
        """
        coupon = CouponFactory(discount=10, valid_to=timezone.now() + timezone.timedelta(days=2))
        self.order.coupon = coupon
        self.order.calculate_total_payable()
        self.order.save()

        # Expire the coupon
        coupon.valid_to = timezone.now() - timezone.timedelta(days=1)
        coupon.save()

        with pytest.raises(ValueError, match=f"The coupon '{coupon.code}' is no longer valid."):
            process_payment(self.drf_request, self.order.order_id)

    def test_payment_fails_if_coupon_usage_limit_reached(self):
        """
        Verify payment fails if a coupon's usage limit is reached between
        order creation and payment.
        """
        coupon = CouponFactory(discount=15, max_usage=5, usage_count=4)
        self.order.coupon = coupon
        self.order.calculate_total_payable()
        self.order.save()

        # Max out the coupon usage
        coupon.usage_count = 5
        coupon.save()

        with pytest.raises(ValueError, match=f"The coupon '{coupon.code}' has reached its usage limit."):
            process_payment(self.drf_request, self.order.order_id)

    def test_payment_fails_if_subtotal_drops_below_coupon_minimum(self):
        """
        Verify payment fails if the order subtotal drops below the coupon's
        minimum required amount due to a price change.
        """
        # Subtotal is 2 * 100.00 = 200.00
        coupon = CouponFactory(discount=10, min_purchase_amount=Decimal("150.00"))
        self.order.coupon = coupon
        self.order.calculate_total_payable()
        self.order.save()

        # Product price drops, making subtotal (2 * 70.00 = 140.00) less than minimum
        self.product.price = Decimal("70.00")
        self.product.save()

        expected_error_msg = "Order subtotal does not meet the minimum purchase amount"
        with pytest.raises(ValueError, match=expected_error_msg):
            process_payment(self.drf_request, self.order.order_id)

    def test_payment_fails_if_stock_becomes_insufficient(self):
        """
        Verify payment fails if product stock is depleted between order creation
        and payment.
        """
        # Order requires 2 items, stock is 10.
        self.product.stock = 1
        self.product.save()

        with pytest.raises(ValueError, match=f"Insufficient stock for product: {self.product.name}"):
            process_payment(self.drf_request, self.order.order_id)
