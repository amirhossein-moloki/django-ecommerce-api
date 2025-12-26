
import pytest
from decimal import Decimal
from datetime import timedelta
from unittest.mock import MagicMock
import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from account.tests.factories import UserFactory
from shop.tests.factories import ProductFactory, CategoryFactory, ProductVariantFactory
from discounts.models import Discount, DiscountRule, UserDiscountUsage
from discounts.services import DiscountService

# Factories for Discount and DiscountRule
class DiscountFactory(DjangoModelFactory):
    class Meta:
        model = Discount

    name = factory.Faker("sentence", nb_words=2)
    type = Discount.DISCOUNT_TYPE_PERCENTAGE
    amount = Decimal("10.00")
    valid_from = factory.LazyFunction(timezone.now)
    valid_to = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))
    active = True
    min_purchase_amount = Decimal("0.00")
    max_usage = 100
    usage_per_user = 1


class DiscountRuleFactory(DjangoModelFactory):
    class Meta:
        model = DiscountRule

    discount = factory.SubFactory(DiscountFactory)


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def category1():
    return CategoryFactory()


@pytest.fixture
def category2():
    return CategoryFactory()


@pytest.fixture
def product1(category1):
    # Ensure at least one variant exists
    product = ProductFactory(category=category1)
    if not product.variants.exists():
        ProductVariantFactory(product=product, price=Decimal("100.00"), stock=10)
    else:
        product.variants.update(price=Decimal("100.00"))
    return product


@pytest.fixture
def product2(category2):
    # Ensure at least one variant exists
    product = ProductFactory(category=category2)
    if not product.variants.exists():
        ProductVariantFactory(product=product, price=Decimal("200.00"), stock=10)
    else:
        product.variants.update(price=Decimal("200.00"))
    return product


@pytest.fixture
def mock_cart(product1, product2):
    """A mock cart that depends on product fixtures."""
    cart = MagicMock()

    p1_variant = product1.variants.first()
    p2_variant = product2.variants.first()

    cart.get_total_price.return_value = p1_variant.price + p2_variant.price

    cart_items_list = [
        {
            "variant": p1_variant,
            "quantity": 1,
            "price": p1_variant.price,
            "total_price": p1_variant.price * 1,
        },
        {
            "variant": p2_variant,
            "quantity": 1,
            "price": p2_variant.price,
            "total_price": p2_variant.price * 1,
        }
    ]
    cart.__iter__.return_value = iter(cart_items_list)
    return cart


@pytest.mark.django_db
class TestDiscountService:
    def test_get_applicable_discounts_valid_automatic(self, mock_cart, user):
        """Tests that a valid automatic discount is returned."""
        DiscountFactory(code=None)  # Automatic discount
        discounts = DiscountService.get_applicable_discounts(mock_cart, user)
        assert discounts.count() == 1

    def test_get_applicable_discounts_valid_coded(self, mock_cart, user):
        """Tests that a valid coded discount is returned when code is provided."""
        discount = DiscountFactory(code="TESTCODE")
        discounts = DiscountService.get_applicable_discounts(mock_cart, user, discount_code="TESTCODE")
        assert discounts.count() == 1
        assert discounts.first() == discount

    def test_get_applicable_discounts_expired(self, mock_cart, user):
        """Tests that an expired discount is not returned."""
        DiscountFactory(valid_to=timezone.now() - timedelta(days=1))
        discounts = DiscountService.get_applicable_discounts(mock_cart, user)
        assert discounts.count() == 0

    def test_get_applicable_discounts_not_yet_valid(self, mock_cart, user):
        """Tests that a discount that is not yet valid is not returned."""
        DiscountFactory(valid_from=timezone.now() + timedelta(days=1))
        discounts = DiscountService.get_applicable_discounts(mock_cart, user)
        assert discounts.count() == 0

    def test_get_applicable_discounts_inactive(self, mock_cart, user):
        """Tests that an inactive discount is not returned."""
        DiscountFactory(active=False)
        discounts = DiscountService.get_applicable_discounts(mock_cart, user)
        assert discounts.count() == 0

    def test_get_applicable_discounts_max_usage_reached(self, mock_cart, user):
        """Tests that a discount with max usage reached is not returned."""
        DiscountFactory(max_usage=10, usage_count=10)
        discounts = DiscountService.get_applicable_discounts(mock_cart, user)
        assert discounts.count() == 0

    def test_get_applicable_discounts_min_purchase_not_met(self, mock_cart, user):
        """Tests that a discount is not returned if min purchase amount is not met."""
        mock_cart.get_total_price.return_value = Decimal("50.00")
        DiscountFactory(min_purchase_amount=Decimal("100.00"))
        discounts = DiscountService.get_applicable_discounts(mock_cart, user)
        assert discounts.count() == 0

    def test_get_applicable_discounts_user_usage_limit_reached(self, mock_cart, user):
        """Tests that a discount is not returned for a user who reached the usage limit."""
        discount = DiscountFactory(usage_per_user=2)
        UserDiscountUsage.objects.create(user=user, discount=discount, usage_count=2)
        discounts = DiscountService.get_applicable_discounts(mock_cart, user, discount_code=discount.code)
        assert discounts.count() == 0

    def test_get_applicable_discounts_user_usage_limit_not_reached(self, mock_cart, user):
        """Tests that a discount is returned for a user who has not reached the usage limit."""
        discount = DiscountFactory(usage_per_user=2)
        UserDiscountUsage.objects.create(user=user, discount=discount, usage_count=1)
        discounts = DiscountService.get_applicable_discounts(mock_cart, user, discount_code=discount.code)
        assert discounts.count() == 1

    def test_apply_discount_percentage_no_rules(self, mock_cart, user):
        """Tests a percentage discount is calculated correctly on the whole cart."""
        DiscountFactory(type=Discount.DISCOUNT_TYPE_PERCENTAGE, amount=Decimal("10.00"), code=None)
        # Total cart price is 300.00, so 10% is 30.00
        amount, discount_obj = DiscountService.apply_discount(mock_cart, user)
        assert amount == Decimal("30.00")
        assert discount_obj is not None

    def test_apply_discount_fixed_amount_no_rules(self, mock_cart, user):
        """Tests a fixed amount discount is calculated correctly."""
        DiscountFactory(type=Discount.DISCOUNT_TYPE_FIXED, amount=Decimal("50.00"), code=None)
        amount, discount_obj = DiscountService.apply_discount(mock_cart, user)
        assert amount == Decimal("50.00")
        assert discount_obj is not None

    def test_apply_discount_fixed_amount_higher_than_total(self, mock_cart, user):
        """Tests fixed discount is capped at the total price."""
        mock_cart.get_total_price.return_value = Decimal("40.00")
        DiscountFactory(type=Discount.DISCOUNT_TYPE_FIXED, amount=Decimal("50.00"), code=None)
        amount, discount_obj = DiscountService.apply_discount(mock_cart, user)
        assert amount == Decimal("40.00") # Should be capped at 40.00

    def test_apply_discount_chooses_best_automatic(self, mock_cart, user):
        """Tests that the best automatic discount is chosen when multiple are valid."""
        DiscountFactory(type=Discount.DISCOUNT_TYPE_PERCENTAGE, amount=Decimal("10.00"), code=None) # 30.00
        DiscountFactory(type=Discount.DISCOUNT_TYPE_FIXED, amount=Decimal("35.00"), code=None) # 35.00
        amount, discount_obj = DiscountService.apply_discount(mock_cart, user)
        assert amount == Decimal("35.00")
        assert discount_obj.type == Discount.DISCOUNT_TYPE_FIXED

    def test_apply_discount_with_code_overrides_automatic(self, mock_cart, user):
        """Tests that a provided discount code takes precedence over automatic discounts."""
        DiscountFactory(type=Discount.DISCOUNT_TYPE_FIXED, amount=Decimal("50.00"), code=None)
        coded_discount = DiscountFactory(code="TESTCODE", type=Discount.DISCOUNT_TYPE_PERCENTAGE, amount=Decimal("10.00")) # 30.00
        amount, discount_obj = DiscountService.apply_discount(mock_cart, user, discount_code="TESTCODE")
        assert amount == Decimal("30.00")
        assert discount_obj == coded_discount

    def test_apply_discount_with_category_rule(self, mock_cart, user, product1, category1):
        """Tests that discount is applied only to products in the specified category."""
        discount = DiscountFactory(type=Discount.DISCOUNT_TYPE_PERCENTAGE, amount=Decimal("10.00"), code=None)
        rule = DiscountRuleFactory(discount=discount)
        rule.categories.add(category1)
        # product1 has price 100.00 and is in category1. product2 is 200.00.
        # Discount should only apply to product1. 10% of 100.00 is 10.00.
        amount, discount_obj = DiscountService.apply_discount(mock_cart, user)
        assert amount == Decimal("10.00")

    def test_apply_discount_with_product_rule(self, mock_cart, user, product2):
        """Tests that discount is applied only to the specified product."""
        discount = DiscountFactory(type=Discount.DISCOUNT_TYPE_PERCENTAGE, amount=Decimal("20.00"), code=None)
        rule = DiscountRuleFactory(discount=discount)
        rule.products.add(product2)
        # product2 has price 200.00. 20% of 200.00 is 40.00.
        amount, discount_obj = DiscountService.apply_discount(mock_cart, user)
        assert amount == Decimal("40.00")

    def test_apply_discount_no_applicable_rules(self, mock_cart, user, category2):
        """Tests that discount is zero if no cart items match the rules."""
        other_category = CategoryFactory()
        discount = DiscountFactory(type=Discount.DISCOUNT_TYPE_PERCENTAGE, amount=Decimal("10.00"), code=None)
        rule = DiscountRuleFactory(discount=discount)
        rule.categories.add(other_category)
        amount, discount_obj = DiscountService.apply_discount(mock_cart, user)
        assert amount == Decimal("0.00")

    def test_record_discount_usage(self, user):
        """Tests that discount usage is recorded correctly for both the discount and the user."""
        discount = DiscountFactory(usage_count=5)

        DiscountService.record_discount_usage(discount, user)

        discount.refresh_from_db()
        assert discount.usage_count == 6

        user_usage = UserDiscountUsage.objects.get(user=user, discount=discount)
        assert user_usage.usage_count == 1

        # Test incrementing existing usage
        DiscountService.record_discount_usage(discount, user)
        user_usage.refresh_from_db()
        assert user_usage.usage_count == 2
