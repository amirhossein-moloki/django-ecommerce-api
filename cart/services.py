from django.shortcuts import get_object_or_404
from shop.models import Product
from .cart import Cart


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
    product = get_object_or_404(Product, id=product_id)
    cart.add(
        product=product,
        quantity=quantity,
        override_quantity=override_quantity
    )


def remove_from_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)


def clear_cart(request):
    cart = Cart(request)
    cart.clear()
