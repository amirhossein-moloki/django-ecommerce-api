from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from account.models import Address
from cart.cart import Cart
from coupons.models import Coupon
from orders.models import Order, OrderItem
from shop.models import Product, ProductVariant
from discounts.services import DiscountService


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for the OrderItem model.
    Provides detailed information about a product within an order.
    """

    price = serializers.DecimalField(max_digits=10, decimal_places=2, source="get_cost")

    class Meta:
        model = OrderItem
        fields = ("product_name", "product_sku", "quantity", "price")


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for the Order model (read-only).
    Provides comprehensive details about an order, including its items.
    """

    items = OrderItemSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField()
    address = serializers.StringRelatedField()
    discount = serializers.StringRelatedField()
    status = serializers.CharField(source="get_status_display")
    payment_status = serializers.CharField(source="get_payment_status_display")

    class Meta:
        model = Order
        fields = (
            "order_id",
            "user",
            "address",
            "order_date",
            "updated",
            "status",
            "discount",
            "currency",
            "discount_amount",
            "payment_gateway",
            "payment_status",
            "shipping_cost",
            "shipping_provider",
            "shipping_tracking_code",
            "subtotal",
            "tax_amount",
            "total_payable",
            "items",
        )


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new order.
    Handles the logic of order creation from the user's cart using the new discount system.
    """

    address_id = serializers.IntegerField()
    discount_code = serializers.CharField(required=False, allow_blank=True)

    def _get_cart(self):
        request = self.context["request"]
        return getattr(request, "cart", Cart(request))

    def validate_address_id(self, value):
        """
        Validate that the address exists and belongs to the current user.
        """
        user = self.context["request"].user
        try:
            address = Address.objects.get(id=value, user=user)
        except Address.DoesNotExist:
            raise ValidationError("The selected address is invalid.")
        return address

    def validate(self, data):
        """Validate discount code."""
        cart = self._get_cart()
        user = self.context["request"].user
        code = data.get("discount_code")
        if code:
            # Check if the discount code is valid
            applicable_discounts = DiscountService.get_applicable_discounts(
                cart, user, discount_code=code
            )
            if not applicable_discounts.exists():
                raise ValidationError(
                    {"discount_code": "This discount code is invalid or has expired."}
                )
        return data

    def save(self, **kwargs):
        """
        Create and save the order and its items from the cart, applying the best discount.
        """
        cart = self._get_cart()
        if len(cart) == 0:
            raise ValidationError("Your cart is empty.")

        user = self.context["request"].user
        address = self.validated_data["address_id"]
        discount_code = self.validated_data.get("discount_code")

        with transaction.atomic():
            # Apply discount (either coded or automatic)
            discount_amount, discount_object = DiscountService.apply_discount(
                cart, user, discount_code
            )

            # Lock products to prevent race conditions
            variant_ids = [item["variant"].variant_id for item in cart]
            locked_variants = list(
                ProductVariant.objects.select_for_update().filter(
                    variant_id__in=variant_ids
                )
            )

            if len(locked_variants) != len(variant_ids):
                raise ValidationError(
                    "Some products in your cart are no longer available."
                )

            locked_variants_map = {v.variant_id: v for v in locked_variants}

            # Create the order with discount information
            order = Order.objects.create(
                user=user,
                address=address,
                discount=discount_object,
                discount_amount=discount_amount,
            )

            items_to_create = []
            variants_to_update = []

            for item in cart:
                variant = locked_variants_map.get(item["variant"].variant_id)

                # Re-validate stock at the moment of purchase
                if variant.stock < item["quantity"]:
                    raise ValidationError(
                        f"Not enough stock for {variant.product.name}."
                    )

                # Price snapshotting is handled by the Cart logic, assuming it's up-to-date

                variant.stock -= item["quantity"]
                variants_to_update.append(variant)

                items_to_create.append(
                    OrderItem(
                        order=order,
                        variant=variant,
                        product_name=variant.product.name,
                        product_sku=variant.sku,
                        quantity=item["quantity"],
                        price=item[
                            "price"
                        ],  # Use price from cart to preserve it at time of order
                    )
                )

            OrderItem.objects.bulk_create(items_to_create)
            ProductVariant.objects.bulk_update(variants_to_update, ["stock"])

            # Record discount usage after the order is successfully created
            if discount_object:
                DiscountService.record_discount_usage(discount_object, user)

            # Set shipping and tax (assuming fixed values for now)
            order.shipping_cost = Decimal("15.00")
            order.tax_amount = order.get_total_cost_before_discount() * Decimal("0.09")

            # Calculate final order total
            order.calculate_total_payable()
            order.save()

            cart.clear()

            return order
