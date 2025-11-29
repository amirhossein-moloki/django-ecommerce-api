from django.utils import timezone
from cart.cart import Cart
from .models import Coupon


def apply_coupon(request, code):
    cart = Cart(request)
    try:
        coupon = Coupon.objects.get(code__iexact=code, active=True)
    except Coupon.DoesNotExist:
        raise ValueError("Invalid or inactive coupon code.")

    if not coupon.is_valid():
        raise ValueError("Coupon is not valid at this time.")

    if coupon.usage_count >= coupon.max_usage:
        raise ValueError("This coupon has reached its usage limit.")

    if cart.get_total_price() < coupon.min_purchase_amount:
        raise ValueError(f"A minimum purchase of {coupon.min_purchase_amount} is required to use this coupon.")

    request.session['coupon_id'] = coupon.id
    return coupon


def update_coupon(instance, data):
    if 'code' in data and data['code'] != instance.code:
        raise ValueError("Coupon code cannot be modified.")
    for key, value in data.items():
        setattr(instance, key, value)
    instance.save()
    return instance


def deactivate_coupon(instance):
    instance.active = False
    instance.save()
    return instance
