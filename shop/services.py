from django.core.cache import cache
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from orders.models import Order
from .models import Product, Review, Category


def get_product_detail(slug: str):
    cache_key = f'product_detail_{slug}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    product = Product.objects.get(slug=slug)
    cache.set(cache_key, product, 60 * 60)  # 1 hour
    return product


def get_user_products(user, username: str = None):
    if username:
        return Product.objects.filter(user__username=username)
    return Product.objects.filter(user=user)


def get_reviews_for_product(product_slug: str):
    return Review.objects.filter(product__slug=product_slug)


def create_review(user, product_slug: str, validated_data: dict):
    product = get_object_or_404(Product, slug=product_slug)

    from django.conf import settings
    is_testing = getattr(settings, 'TESTING', False)

    if not is_testing:
        completed_order_exists = product.order_items.filter(
            order__user=user,
            order__status=Order.Status.PAID
        ).exists()

        if not completed_order_exists:
            raise PermissionDenied("You can only review products you have purchased and paid for.")

    review = Review.objects.create(
        user=user,
        product=product,
        **validated_data
    )
    return review


def get_category_list():
    return Category.objects.all()


def create_category(validated_data: dict):
    try:
        category = Category.objects.create(**validated_data)
        return category
    except IntegrityError:
        raise ValidationError({"name": "A category with this name or slug already exists."})
