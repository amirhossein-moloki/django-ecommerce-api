
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

    cart.add(
        variant=variant,
        quantity=quantity,
        override_quantity=override_quantity,
        allow_insufficient_stock=allow_insufficient_stock,
    )


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
