import redis
import sys
from django.conf import settings
from .models import Product

class Recommender:
    def __init__(self, redis_client=None):
        if redis_client:
            self.r = redis_client
        elif "test" in sys.argv:
            from fakeredis import FakeRedis
            self.r = FakeRedis()
        else:
            self.r = redis.from_url(settings.REDIS_URL)

    def get_product_key(self, product_id):
        return f"product:{product_id}:purchased_with"

    def products_bought(self, products):
        product_ids = [p.product_id for p in products]
        for product_id in product_ids:
            for with_id in product_ids:
                if product_id != with_id:
                    self.r.zincrby(self.get_product_key(product_id), 1, with_id)

    def suggest_products_for(self, products, max_results=6):
        product_ids = [p.id for p in products]
        if len(products) == 1:
            suggestions = self.r.zrange(
                self.get_product_key(product_ids[0]), 0, -1, desc=True
            )[:max_results]
        else:
            flat_ids = "".join([str(id) for id in product_ids])
            tmp_key = f"tmp_{flat_ids}"
            keys = [self.get_product_key(id) for id in product_ids]
            self.r.zunionstore(tmp_key, keys)
            self.r.zrem(tmp_key, *product_ids)
            suggestions = self.r.zrange(tmp_key, 0, -1, desc=True)[:max_results]
            self.r.delete(tmp_key)

        # redis returns bytes, so we decode them to utf-8 and cast to int
        suggested_products_ids = [int(id) for id in suggestions]

        # get suggested products and sort by order of appearance
        suggested_products = list(
            Product.objects.filter(id__in=suggested_products_ids)
        )
        suggested_products.sort(
            key=lambda x: suggested_products_ids.index(x.id)
        )
        return suggested_products

    #
    # def suggest_for_user(self, user, max_results=100):
    #     """
    #     Suggest products for the logged-in user based on their previous purchases.
    #     """
    #     # Get the products purchased by the user
    #     purchased_products = Product.objects.filter(
    #         order__user=user
    #     ).distinct()  # Assuming an `Order` model exists with a `user` field
    #
    #     if not purchased_products.exists():
    #         return []  # Return an empty list if no purchases are found
    #
    #     # Use the existing recommendation logic
    #     return self.suggest_products_for(purchased_products, max_results=max_results)
