import pytest
from unittest.mock import patch, Mock
from decimal import Decimal
from django.utils import timezone
from django.test import RequestFactory
from django.urls import reverse

from account.factories import UserFactory
from coupons.factories import CouponFactory
from orders.factories import OrderFactory, OrderItemFactory
from shop.factories import ProductFactory, ProductVariantFactory
from payment.services import process_payment


@pytest.mark.django_db
class TestPaymentRecalculation:
    def setup_method(self):
        self.user = UserFactory.create()
        self.product = ProductFactory.create()
        self.variant = ProductVariantFactory.create(
            product=self.product, price=Decimal("100.00"), stock=10
        )
        self.order = OrderFactory.create(user=self.user, coupon=None)
        self.order_item = OrderItemFactory.create(
            order=self.order, variant=self.variant, quantity=2, price=self.variant.price
        )
        self.order.calculate_total_payable()
        self.order.save()

        # Create a mock request object that has the necessary attributes
        self.mock_request = Mock()
        self.mock_request.user = self.user
        self.mock_request.build_absolute_uri.return_value = "http://testserver" + reverse('payment:verify')


    @patch('payment.services.ZibalGateway.create_payment_request')
    def test_recalculation_on_product_price_change(self, mock_create_request):
        mock_create_request.return_value = {'trackId': 'zibal-12345', 'result': 100}
        self.variant.price = Decimal("120.00")
        self.variant.save()
        process_payment(self.mock_request, self.order.order_id)
        self.order.refresh_from_db()
        assert self.order.subtotal == Decimal("240.00")
        mock_create_request.assert_called_once()
        called_kwargs = mock_create_request.call_args.kwargs
        assert called_kwargs['amount'] == 24000

    def test_payment_fails_if_coupon_expires(self):
        coupon = CouponFactory.create(discount=10, valid_to=timezone.now() + timezone.timedelta(days=2))
        self.order.coupon = coupon
        self.order.calculate_total_payable()
        self.order.save()
        coupon.valid_to = timezone.now() - timezone.timedelta(days=1)
        coupon.save()
        with pytest.raises(ValueError, match=f"The coupon '{coupon.code}' is no longer valid."):
            process_payment(self.mock_request, self.order.order_id)
