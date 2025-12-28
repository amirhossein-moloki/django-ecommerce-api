import pytest
from decimal import Decimal
from datetime import timedelta
from unittest.mock import MagicMock, patch

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from coupons.models import Coupon
from coupons.services import apply_coupon


class CouponFactory(DjangoModelFactory):
    class Meta:
        model = Coupon

    code = factory.Faker("word")
    valid_from = factory.LazyFunction(timezone.now)
    valid_to = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))
    discount = 10
    max_usage = 100
    usage_count = 0
    min_purchase_amount = Decimal("50.00")
    active = True


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.session = {}
    return request


@pytest.mark.django_db
@patch("coupons.services.Cart")
class TestCouponService:
    def test_apply_coupon_valid(self, mock_cart_class, mock_request):
        """Tests that a valid coupon is applied successfully."""
        mock_cart_instance = mock_cart_class.return_value
        mock_cart_instance.get_total_price.return_value = Decimal("100.00")
        coupon = CouponFactory(code="VALID")

        result = apply_coupon(mock_request, "VALID")

        assert result == coupon
        assert mock_request.session["coupon_id"] == coupon.id

    def test_apply_coupon_not_found(self, mock_cart_class, mock_request):
        """Tests that ValueError is raised for a non-existent coupon."""
        with pytest.raises(ValueError, match="Invalid or inactive coupon code."):
            apply_coupon(mock_request, "NONEXISTENT")

    def test_apply_coupon_expired(self, mock_cart_class, mock_request):
        """Tests that ValueError is raised for an expired coupon."""
        CouponFactory(code="EXPIRED", valid_to=timezone.now() - timedelta(days=1))
        with pytest.raises(ValueError, match="Coupon is not valid at this time."):
            apply_coupon(mock_request, "EXPIRED")

    def test_apply_coupon_not_yet_valid(self, mock_cart_class, mock_request):
        """Tests that ValueError is raised for a coupon that is not yet valid."""
        CouponFactory(code="FUTURE", valid_from=timezone.now() + timedelta(days=1))
        with pytest.raises(ValueError, match="Coupon is not valid at this time."):
            apply_coupon(mock_request, "FUTURE")

    def test_apply_coupon_inactive(self, mock_cart_class, mock_request):
        """Tests that ValueError is raised for an inactive coupon."""
        CouponFactory(code="INACTIVE", active=False)
        with pytest.raises(ValueError, match="Invalid or inactive coupon code."):
            apply_coupon(mock_request, "INACTIVE")

    def test_apply_coupon_max_usage_reached(self, mock_cart_class, mock_request):
        """Tests that ValueError is raised when max usage is reached."""
        CouponFactory(code="MAXED", max_usage=10, usage_count=10)
        with pytest.raises(
            ValueError, match="This coupon has reached its usage limit."
        ):
            apply_coupon(mock_request, "MAXED")

    def test_apply_coupon_min_purchase_not_met(self, mock_cart_class, mock_request):
        """Tests that ValueError is raised if min purchase amount is not met."""
        mock_cart_instance = mock_cart_class.return_value
        mock_cart_instance.get_total_price.return_value = Decimal("40.00")
        coupon = CouponFactory(code="MINPURCHASE", min_purchase_amount=Decimal("50.00"))

        expected_error = f"A minimum purchase of {coupon.min_purchase_amount} is required to use this coupon."
        with pytest.raises(ValueError, match=expected_error):
            apply_coupon(mock_request, "MINPURCHASE")
