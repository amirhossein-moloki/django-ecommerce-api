from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from shop.models import Product, Category, ProductVariant
from account.models import UserAccount
from decimal import Decimal
from unittest.mock import patch


class ProductViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserAccount.objects.create_user(phone_number="123456789", password="testpassword")
        cls.category = Category.objects.create(name="Test Category", slug="test-category")
        products = []
        for i in range(15):
            product = Product.objects.create(
                name=f"Product {i:02d}",
                slug=f"product-{i}",
                category=cls.category,
                user=cls.user,
            )
            ProductVariant.objects.create(
                product=product,
                price=Decimal(f"{10 + i}.00"),
                stock=i,
                sku=f"SKU{i}"
            )
            products.append(product)
        cls.products = products
        cls.list_url = reverse("api-v1:product-list")

    def test_product_list_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ordering_by_name_ascending(self):
        response = self.client.get(self.list_url, {"ordering": "name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product_names = [p["name"] for p in response.data["results"]]
        expected_names = [f"Product {i:02d}" for i in range(10)]
        self.assertEqual(product_names, expected_names)

    def test_ordering_by_name_descending(self):
        response = self.client.get(self.list_url, {"ordering": "-name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product_names = [p["name"] for p in response.data["results"]]
        expected_names = [f"Product {i:02d}" for i in range(14, 4, -1)]
        self.assertEqual(product_names, expected_names)

    def test_ordering_by_price_ascending(self):
        response = self.client.get(self.list_url, {"ordering": "price"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The serializer now nests variants, so we access the price through it.
        prices = [p['variants'][0]['price'] for p in response.data['results']]
        expected_prices = [f"{Decimal(f'{10 + i}.00'):.2f}" for i in range(10)]
        self.assertEqual(prices, expected_prices)

    def test_ordering_by_price_descending(self):
        response = self.client.get(self.list_url, {"ordering": "-price"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [p['variants'][0]['price'] for p in response.data['results']]
        expected_prices = [f"{Decimal(f'{10 + i}.00'):.2f}" for i in range(14, 4, -1)]
        self.assertEqual(prices, expected_prices)

    def test_ordering_by_invalid_field(self):
        response = self.client.get(self.list_url, {"ordering": "invalid_field"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10) # Default page size

    def test_pagination_structure(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 15)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_pagination_page_size(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10) # Default page size from PaginationMixin

    def test_pagination_second_page(self):
        response = self.client.get(self.list_url, {"page": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

    @patch("shop.views.Recommender")
    def test_recommendations_action(self, mock_recommender):
        # Setup the mock
        mock_recommender_instance = mock_recommender.return_value
        recommended_products = self.products[2:4]  # Recommend product 2 and 3
        mock_recommender_instance.suggest_products_for.return_value = recommended_products

        target_product = self.products[0]
        url = reverse("api-v1:product-recommendations", kwargs={"slug": target_product.slug})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the mocked recommender was called correctly
        mock_recommender_instance.suggest_products_for.assert_called_once()
        called_with_product_list = mock_recommender_instance.suggest_products_for.call_args[0][0]
        self.assertEqual(len(called_with_product_list), 1)
        self.assertEqual(called_with_product_list[0].id, target_product.id)

        # Check the response data
        self.assertEqual(len(response.data), 2)
        recommended_slugs = {p["slug"] for p in response.data}
        self.assertEqual(recommended_slugs, {"product-2", "product-3"})
