from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Category, Product, Review


@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    """
    Invalidate the category list cache when a category is saved or deleted.
    """
    cache.delete("category_list")


@receiver([post_save, post_delete], sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    """
    Invalidate product-related caches when a product is saved or deleted.
    """
    cache.delete("product_list")
    cache.delete(f"product_{instance.slug}")


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
