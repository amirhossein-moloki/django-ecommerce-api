from decimal import Decimal
from django.db.models import F, Q
from django.utils import timezone
from .models import Discount, UserDiscountUsage

class DiscountService:
    @staticmethod
    def get_applicable_discounts(cart, user, discount_code=None):
        """
        Filters and returns applicable discounts. If a code is provided, it fetches that specific discount.
        Otherwise, it fetches all applicable automatic (codeless) discounts.
        """
        now = timezone.now()
        total_price = cart.get_total_price()

        base_filters = Q(
            active=True,
            valid_from__lte=now,
            valid_to__gte=now,
            min_purchase_amount__lte=total_price,
            usage_count__lt=F('max_usage')
        )

        if discount_code:
            discounts = Discount.objects.filter(base_filters & Q(code__iexact=discount_code))
        else:
            discounts = Discount.objects.filter(base_filters & Q(code__isnull=True))

        if user.is_authenticated:
            user_usages = UserDiscountUsage.objects.filter(user=user, discount__in=discounts).select_related('discount')
            excluded_ids = [usage.discount.id for usage in user_usages if usage.usage_count >= usage.discount.usage_per_user]
            if excluded_ids:
                discounts = discounts.exclude(id__in=excluded_ids)

        return discounts

    @staticmethod
    def apply_discount(cart, user, discount_code=None):
        """
        Calculates the discount for the cart. If a code is provided, it applies that discount.
        Otherwise, it finds and applies the best automatic discount.
        Returns the discount amount and the discount object.
        """
        discounts_qs = DiscountService.get_applicable_discounts(cart, user, discount_code).prefetch_related(
            'rules__products', 'rules__categories', 'rules__tags', 'rules__variants'
        )

        if discount_code:
            discount = discounts_qs.first()
            if not discount:
                return Decimal('0.00'), None

            amount = DiscountService._calculate_single_discount_amount(cart, discount)
            return amount, discount

        else: # Find the best automatic discount
            best_amount = Decimal('0.00')
            best_discount = None
            for discount in discounts_qs:
                amount = DiscountService._calculate_single_discount_amount(cart, discount)
                if amount > best_amount:
                    best_amount = amount
                    best_discount = discount
            return best_amount, best_discount

    @staticmethod
    def _calculate_single_discount_amount(cart, discount):
        """Helper method to calculate the amount for a single discount."""
        cart_items = list(cart)
        eligible_price = Decimal('0.00')
        rules = list(discount.rules.all())

        if not any(rule.products.exists() or rule.categories.exists() or rule.tags.exists() or rule.variants.exists() for rule in rules):
            eligible_price = cart.get_total_price()
        else:
            eligible_product_ids = set()
            eligible_category_ids = set()
            eligible_tag_ids = set()
            eligible_variant_ids = set()

            for rule in rules:
                eligible_product_ids.update(p.product_id for p in rule.products.all())
                eligible_category_ids.update(c.id for c in rule.categories.all())
                eligible_tag_ids.update(t.id for t in rule.tags.all())
                eligible_variant_ids.update(v.variant_id for v in rule.variants.all())

            for item in cart_items:
                variant = item['variant']
                product = variant.product
                product_tags = set(product.tags.values_list('id', flat=True))

                if (variant.variant_id in eligible_variant_ids or
                    product.product_id in eligible_product_ids or
                    product.category_id in eligible_category_ids or
                    not product_tags.isdisjoint(eligible_tag_ids)):
                    eligible_price += item['total_price']

        if eligible_price > 0:
            if discount.type == Discount.DISCOUNT_TYPE_PERCENTAGE:
                return (discount.amount / Decimal('100')) * eligible_price
            elif discount.type == Discount.DISCOUNT_TYPE_FIXED:
                return min(discount.amount, eligible_price)

        return Decimal('0.00')

    @staticmethod
    def record_discount_usage(discount, user):
        """
        Atomically increments the usage count for a discount and for the specific user.
        """
        if discount:
            # Increment the overall usage count
            Discount.objects.filter(id=discount.id).update(usage_count=F('usage_count') + 1)

            # Record or update the user-specific usage
            if user.is_authenticated:
                usage, created = UserDiscountUsage.objects.get_or_create(
                    user=user,
                    discount=discount,
                    defaults={'usage_count': 1}
                )
                if not created:
                    usage.usage_count = F('usage_count') + 1
                    usage.save(update_fields=['usage_count'])
