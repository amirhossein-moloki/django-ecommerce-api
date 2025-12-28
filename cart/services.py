from rest_framework.exceptions import ValidationError

from shop.models import ProductVariant

from .cart import Cart


def get_cart_data(request):
    cart = Cart(request)
    return {
        "items": [
            {
                "variant": item["variant"],
                "quantity": item["quantity"],
                "total_price": item["total_price"],
            }
            for item in cart
        ],
        "total_price": cart.get_total_price(),
    }


def add_to_cart(
    request,
    variant_id,
    quantity=1,
    override_quantity=False,
    allow_insufficient_stock=False,
):
    cart = Cart(request)
    try:
        variant = ProductVariant.objects.get(variant_id=variant_id)
    except ProductVariant.DoesNotExist:
        # Re-raise the exception to be caught by the view layer.
        raise

    if variant.stock == 0:
        raise ValidationError("This product is out of stock.")

    # This logic should be in the Cart class itself, but for now, we adapt the service
    current_quantity = 0
    if cart.cart:
        item = cart.cart.items.filter(variant=variant).first()
        if item:
            current_quantity = item.quantity

    if override_quantity:
        total_quantity = quantity
    else:
        total_quantity = current_quantity + quantity

    if total_quantity > variant.stock and not allow_insufficient_stock:
        raise ValidationError(
            f"Cannot add {quantity} items. Only {variant.stock - current_quantity} "
            f"more items can be added."
        )

    cart.add(variant=variant, quantity=quantity, override_quantity=override_quantity)


def remove_from_cart(request, variant_id):
    cart = Cart(request)
    try:
        variant = ProductVariant.objects.get(variant_id=variant_id)
    except ProductVariant.DoesNotExist:
        raise
    cart.remove(variant)


def clear_cart(request):
    cart = Cart(request)
    cart.clear()
