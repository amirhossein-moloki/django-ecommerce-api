from django.test import TestCase
from shop.recommender import Recommender
from shop.models import Product, Category, ProductVariant
from account.models import UserAccount
from decimal import Decimal
from unittest.mock import patch


class RecommenderTests(TestCase):
    def setUp(self):
        self.user = UserAccount.objects.create_user(phone_number="123456789", password="testpassword")
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.p1 = Product.objects.create(name="Product 1", slug="p1", category=self.category, user=self.user)
        ProductVariant.objects.create(product=self.p1, price=Decimal("10.00"), stock=10, sku="SKU1")
        self.p2 = Product.objects.create(name="Product 2", slug="p2", category=self.category, user=self.user)
        ProductVariant.objects.create(product=self.p2, price=Decimal("20.00"), stock=10, sku="SKU2")
        self.p3 = Product.objects.create(name="Product 3", slug="p3", category=self.category, user=self.user)
        ProductVariant.objects.create(product=self.p3, price=Decimal("30.00"), stock=10, sku="SKU3")
        self.p4 = Product.objects.create(name="Product 4", slug="p4", category=self.category, user=self.user)
        ProductVariant.objects.create(product=self.p4, price=Decimal("40.00"), stock=10, sku="SKU4")

        self.recommender = Recommender()

    @patch("shop.recommender.r")
    def test_products_bought(self, mock_redis):
        products = [self.p1, self.p2, self.p3]
        self.recommender.products_bought(products)

        # Check if zincrby was called correctly
        p1_key = self.recommender.get_product_key(self.p1.id)
        p2_key = self.recommender.get_product_key(self.p2.id)
        p3_key = self.recommender.get_product_key(self.p3.id)

        mock_redis.zincrby.assert_any_call(p1_key, 1, self.p2.id)
        mock_redis.zincrby.assert_any_call(p1_key, 1, self.p3.id)
        mock_redis.zincrby.assert_any_call(p2_key, 1, self.p1.id)
        mock_redis.zincrby.assert_any_call(p2_key, 1, self.p3.id)
        mock_redis.zincrby.assert_any_call(p3_key, 1, self.p1.id)
        mock_redis.zincrby.assert_any_call(p3_key, 1, self.p2.id)
        self.assertEqual(mock_redis.zincrby.call_count, 6)

    @patch("shop.recommender.r")
    def test_suggest_products_for_single_product(self, mock_redis):
        # Mock the return value of zrange to be bytes
        mock_redis.zrange.return_value = [str(self.p2.id).encode(), str(self.p3.id).encode()]

        suggestions = self.recommender.suggest_products_for([self.p1])

        p1_key = self.recommender.get_product_key(self.p1.id)
        mock_redis.zrange.assert_called_once_with(p1_key, 0, -1, desc=True)

        suggestion_ids = {p.id for p in suggestions}
        self.assertEqual(suggestion_ids, {self.p2.id, self.p3.id})

    @patch("shop.recommender.r")
    def test_suggest_products_for_multiple_products(self, mock_redis):
        products = [self.p1, self.p4]
        product_ids = [p.id for p in products]

        # Mock the zunionstore, zrem, and zrange calls
        mock_redis.zrange.return_value = [str(self.p2.id).encode(), str(self.p3.id).encode()]

        suggestions = self.recommender.suggest_products_for(products)

        flat_ids = "".join([str(id) for id in product_ids])
        tmp_key = f"tmp_{flat_ids}"
        keys = [self.recommender.get_product_key(id) for id in product_ids]

        mock_redis.zunionstore.assert_called_once_with(tmp_key, keys)
        mock_redis.zrem.assert_called_once_with(tmp_key, *product_ids)
        mock_redis.zrange.assert_called_once_with(tmp_key, 0, -1, desc=True)
        mock_redis.delete.assert_called_once_with(tmp_key)

        suggestion_ids = {p.id for p in suggestions}
        self.assertEqual(suggestion_ids, {self.p2.id, self.p3.id})
