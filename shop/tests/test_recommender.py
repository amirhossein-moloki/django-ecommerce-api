import pytest
from unittest.mock import patch
from shop.recommender import Recommender
from shop.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


@patch('shop.recommender.redis.Redis')
def test_recommender_product_suggestion(MockRedis):
    """
    Tests the product recommendation functionality.
    """
    mock_redis_instance = MockRedis.return_value
    recommender = Recommender(redis_client=mock_redis_instance)

    # Create some products
    p1 = ProductFactory(tags=["coffee", "hot"])
    p2 = ProductFactory(tags=["tea", "hot"])
    p3 = ProductFactory(tags=["coffee", "cold"])

    # Simulate buying p1 and p3 together
    recommender.products_bought([p1, p3])

    # Suggestions for a product bought with p1 should include p3
    suggested_for_p1 = recommender.suggest_products_for([p1])
    assert p3 in suggested_for_p1

    # Suggestions for a product bought with p3 should include p1
    suggested_for_p3 = recommender.suggest_products_for([p3])
    assert p1 in suggested_for_p3

    # Suggestions for a product never bought with others should be empty
    suggested_for_p2 = recommender.suggest_products_for([p2])
    assert len(suggested_for_p2) == 0
