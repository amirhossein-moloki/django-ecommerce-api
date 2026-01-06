from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Category, Product, Review


@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    """
    Invalidate the category list cache when a category is saved or deleted.
    """
    # This key is simple and doesn't need a pattern.
    cache.delete("category_list")


@receiver([post_save, post_delete], sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    """
    Invalidate product-related caches when a product is saved or deleted.

    - Deletes the specific cache for the product's detail view.
    - Deletes all versions of the product list cache using a pattern.
      This is crucial to ensure that any filtered or sorted list view
      is also invalidated.
    """
    # Invalidate the detail view cache for this specific product
    cache.delete(f"product_detail_{instance.slug}")

    # Invalidate all product list caches (covers all query param variations)
    # The key pattern is defined in caching.py as "product_list:*"
    delete_pattern = getattr(cache, "delete_pattern", None)
    if callable(delete_pattern):
        delete_pattern("product_list:*")
        return

    iter_keys = getattr(cache, "iter_keys", None)
    if callable(iter_keys):
        keys = list(iter_keys("product_list:*"))
        if keys:
            cache.delete_many(keys)
        return

    keys = getattr(cache, "keys", None)
    if callable(keys):
        pattern_keys = keys("product_list:*")
        if pattern_keys:
            cache.delete_many(pattern_keys)
        return

    cache.clear()


@receiver(post_save, sender=Review)
def update_rating_on_review_save(sender, instance, **kwargs):
    """
    Update the product's rating when a review is saved.
    """
    instance.product.update_rating_and_reviews_count()


@receiver(post_delete, sender=Review)
def update_rating_on_review_delete(sender, instance, **kwargs):
    """
    Update the product's rating when a review is deleted.
    """
    instance.product.update_rating_and_reviews_count()
