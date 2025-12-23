import pytest
from unittest.mock import MagicMock
from shop.utils import product_upload_to_unique, search_products
from shop.factories import ProductFactory

pytestmark = pytest.mark.django_db


class TestShopUtils:
    def test_product_upload_to_unique(self):
        # Create a mock product instance
        mock_instance = MagicMock()
        filename = "test_image.jpg"

        # Call the function
        path = product_upload_to_unique(mock_instance, filename)

        # Assert the path starts with 'products/' and ends with '.jpg'
        assert path.startswith("products/")
        assert path.endswith(".jpg")
        # Check that the original filename is not in the new path (it should be unique)
        assert "test_image" not in path

    def test_search_products(self):
        # Create some products
        p1 = ProductFactory(name="Laptop Pro", description="A powerful laptop for professionals.")
        p2 = ProductFactory(name="Gaming Mouse", description="A high-precision mouse for gaming.")
        p3 = ProductFactory(name="Mechanical Keyboard", description="A keyboard with mechanical switches.")

        # Get the base queryset
        queryset = p1.__class__.objects.all()

        # Test search by name
        results_name = search_products(queryset, "Laptop")
        assert results_name.count() == 1
        assert p1 in results_name

        # Test search by description
        results_desc = search_products(queryset, "gaming")
        assert results_desc.count() == 1
        assert p2 in results_desc

        # Test combined search (name or description)
        results_combined = search_products(queryset, "key")
        assert results_combined.count() == 1
        assert p3 in results_combined

        # Test no results
        results_none = search_products(queryset, "nonexistent")
        assert results_none.count() == 0

        # Test empty search term
        results_empty = search_products(queryset, "")
        assert results_empty.count() == 3
