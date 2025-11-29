from django.core.cache import cache
from django.db.models import Avg, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Product, Category, Review


# -----------------------------------------------------------------------------
# C A C H E   I N V A L I D A T I O N   S I G N A L S
# -----------------------------------------------------------------------------

@receiver([post_save, post_delete], sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    """
    Invalidate cache related to products when a product is saved or deleted.
    This ensures that product lists and detail pages show fresh data.
    """
    # Invalidate the main product list cache (used in ProductViewSet list)
    cache.delete('product_list')

    # Invalidate the cache for the specific product detail view
    cache.delete(f'product_detail_{instance.slug}')

    # Since changing a product might affect category lists (e.g., through relations),
    # it's safest to invalidate the category list cache as well.
    cache.delete('category_list_custom')


@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    """
    Invalidate the category list cache when a category is saved or deleted.
    """
    cache.delete('category_list_custom')


# -----------------------------------------------------------------------------
# R A T I N G   U P D A T E   S I G N A L S
# -----------------------------------------------------------------------------

@receiver(post_save, sender=Review)
def update_rating_on_review_save(sender, instance, created, **kwargs):
    """
    Update the product's average rating and reviews count when a review is saved.
    """
    instance.product.update_rating_and_reviews_count()


@receiver(post_delete, sender=Review)
def update_rating_on_review_delete(sender, instance, **kwargs):
    """
    Update the product's average rating and reviews count when a review is deleted.
    """
    instance.product.update_rating_and_reviews_count()
