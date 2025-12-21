from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from shop.models import Product

from .cart import Cart
from .models import CartItem


def get_cart_data(request):
    cart = Cart(request)
    return {
        'items': [
            {
                'product': item['product'],
                'quantity': item['quantity'],
                'total_price': item['total_price'],
            }
            for item in cart
        ],
        'total_price': cart.get_total_price(),
    }


def add_to_cart(request, product_id, quantity=1, override_quantity=False):
    cart = Cart(request)
    product = get_object_or_404(Product, product_id=product_id)

    if product.stock == 0:
        raise ValidationError("This product is out of stock.")

    cart_item = cart.cart.items.filter(product=product).first()
    current_quantity = cart_item.quantity if cart_item else 0

    if override_quantity:
        total_quantity = quantity
    else:
        total_quantity = current_quantity + quantity

    if total_quantity > product.stock:
        raise ValidationError(
            f"Cannot add {quantity} items. Only {product.stock - current_quantity} "
            f"more items can be added."
        )

    cart.add(product=product, quantity=quantity, override_quantity=override_quantity)


def remove_from_cart(request, product_id):
    cart = Cart(request)
    # The view will handle fetching the product and catching exceptions
    cart.remove(product_id)


def clear_cart(request):
    cart = Cart(request)
    cart.clear()
