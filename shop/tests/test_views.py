import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from account.tests.factories import UserFactory
from orders.models import Order
from orders.tests.factories import OrderFactory, OrderItemFactory
from shop.tests.factories import (
    ProductFactory,
    CategoryFactory,
    ProductVariantFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


class TestProductViewSet:
    def test_list_products_with_filters_search_and_ordering(self, api_client):
        category = CategoryFactory(name="Accessories")
        matching = ProductFactory(name="Alpha Phone", category=category)
        ProductVariantFactory(product=matching, price=120, stock=10)
        other = ProductFactory(name="Beta Case", category=category)
        ProductVariantFactory(product=other, price=80, stock=0)

        url = reverse("api-v1:product-list")
        response = api_client.get(
            url,
            {
                "search": "Alpha",
                "price_min": 100,
                "price_max": 150,
                "in_stock": True,
                "ordering": "-price",
            },
        )
        assert response.status_code == 200
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["slug"] == matching.slug

    def test_list_products(self, api_client):
        ProductFactory.create_batch(5)
        url = reverse("api-v1:product-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data["data"]) == 5

    def test_retrieve_product(self, api_client):
        product = ProductFactory()
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["slug"] == product.slug

    def test_retrieve_non_existent_product(self, api_client):
        url = reverse("api-v1:product-detail", kwargs={"slug": "non-existent-slug"})
        response = api_client.get(url)
        assert response.status_code == 404

    def test_create_product(self, api_client):
        user = UserFactory()
        category = CategoryFactory()
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:product-list")
        data = {
            "name": "Test Create",
            "description": "A detailed description for the test product.",
            "category": category.pk,
            "weight": 1.5,
            "length": 10,
            "width": 5,
            "height": 2,
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Test Create"

    def test_update_product_permissions_owner(self, api_client):
        owner = UserFactory()
        product = ProductFactory(user=owner)
        api_client.force_authenticate(user=owner)
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.patch(url, {"name": "Updated Name"}, format="json")
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.name == "Updated Name"

    def test_update_product_permissions_non_owner(self, api_client):
        product = ProductFactory()
        other_user = UserFactory()
        api_client.force_authenticate(user=other_user)
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.patch(url, {"name": "Blocked"}, format="json")
        assert response.status_code == 403

    def test_destroy_product_permissions_owner(self, api_client):
        owner = UserFactory()
        product = ProductFactory(user=owner)
        api_client.force_authenticate(user=owner)
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.delete(url)
        assert response.status_code == 204
        product.refresh_from_db()
        assert product.deleted_at is not None

    def test_destroy_product_permissions_non_owner(self, api_client):
        product = ProductFactory()
        other_user = UserFactory()
        api_client.force_authenticate(user=other_user)
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.delete(url)
        assert response.status_code == 403

    def test_list_products_cache_hit_and_miss(self, api_client):
        cache.clear()
        ProductFactory.create_batch(2)
        url = reverse("api-v1:product-list")
        response = api_client.get(url)
        assert response.status_code == 200
        cache_key = "product_list_"
        cached_data = cache.get(cache_key)
        assert cached_data == response.data
        response_cached = api_client.get(url)
        assert response_cached.status_code == 200
        assert response_cached.data == cached_data

    def test_retrieve_product_cache_hit_and_miss(self, api_client):
        cache.clear()
        product = ProductFactory()
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.get(url)
        assert response.status_code == 200
        cache_key = f"product_{product.slug}"
        cached_data = cache.get(cache_key)
        assert cached_data == response.data
        response_cached = api_client.get(url)
        assert response_cached.status_code == 200
        assert response_cached.data == cached_data


class TestCategoryViewSet:
    def test_list_categories(self, api_client):
        CategoryFactory.create_batch(3)
        url = reverse("api-v1:category-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data["data"]) == 3

    def test_create_category_admin_only(self, api_client):
        user = UserFactory(is_staff=False)
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:category-list")
        response = api_client.post(url, {"name": "Forbidden"}, format="json")
        assert response.status_code == 403

        admin = UserFactory(is_staff=True)
        api_client.force_authenticate(user=admin)
        response = api_client.post(url, {"name": "Allowed"}, format="json")
        assert response.status_code == 201

    def test_update_category_admin_only(self, api_client):
        category = CategoryFactory()
        url = reverse("api-v1:category-detail", kwargs={"slug": category.slug})

        user = UserFactory(is_staff=False)
        api_client.force_authenticate(user=user)
        response = api_client.patch(url, {"name": "Blocked"}, format="json")
        assert response.status_code == 403

        admin = UserFactory(is_staff=True)
        api_client.force_authenticate(user=admin)
        response = api_client.patch(url, {"name": "Allowed"}, format="json")
        assert response.status_code == 200

    def test_destroy_category_admin_only(self, api_client):
        category = CategoryFactory()
        url = reverse("api-v1:category-detail", kwargs={"slug": category.slug})

        user = UserFactory(is_staff=False)
        api_client.force_authenticate(user=user)
        response = api_client.delete(url)
        assert response.status_code == 403

        admin = UserFactory(is_staff=True)
        api_client.force_authenticate(user=admin)
        response = api_client.delete(url)
        assert response.status_code == 204


class TestReviewViewSet:
    def test_create_review_permission(self, api_client):
        user = UserFactory()
        product = ProductFactory()
        api_client.force_authenticate(user=user)
        url = reverse(
            "api-v1:product-reviews-list", kwargs={"product_slug": product.slug}
        )
        response = api_client.post(url, {"rating": 5})
        assert response.status_code == 403

    def test_create_review_success(self, api_client):
        user = UserFactory()
        product = ProductFactory()
        order = OrderFactory(user=user)
        order.status = Order.Status.PAID
        order.save(update_fields=["status"])
        variant = ProductVariantFactory(product=product)
        OrderItemFactory(order=order, variant=variant)
        api_client.force_authenticate(user=user)
        url = reverse(
            "api-v1:product-reviews-list", kwargs={"product_slug": product.slug}
        )
        response = api_client.post(url, {"rating": 4})
        assert response.status_code == 201
        assert response.data["rating"] == 4
