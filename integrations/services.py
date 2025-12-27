from typing import List, Dict, Any
from django.http import HttpRequest
from shop.models import ProductVariant


def generate_product_feed_data(request: HttpRequest) -> List[Dict[str, Any]]:
    """
    Fetches active and in-stock product variants and formats them for a feed.

    Args:
        request: The HttpRequest object, used to build absolute URLs.

    Returns:
        A list of dictionaries, where each dictionary represents a product
        variant with the necessary data for the feed.
    """
    variants = ProductVariant.objects.filter(
        stock__gt=0,
        product__deleted_at__isnull=True
    ).select_related('product', 'product__category')

    feed_data = []
    for variant in variants:
        product = variant.product

        # Determine the image URL, preferring the variant's image
        image_obj = variant.image or product.thumbnail
        image_url = request.build_absolute_uri(image_obj.url) if image_obj else ''

        # Build the absolute URL for the product
        product_url = request.build_absolute_uri(product.get_absolute_url())

        feed_data.append({
            'id': variant.sku or str(variant.variant_id),
            'title': product.name,
            'price': variant.price,
            'availability': 'instock',  # Or True, depending on the platform's requirement
            'product_url': product_url,
            'image_url': image_url,
            'category': product.category.name,
        })

    return feed_data
