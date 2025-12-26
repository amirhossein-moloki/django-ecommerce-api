import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from account.tests.factories import UserFactory
from orders.models import Order
from orders.tests.factories import OrderFactory, OrderItemFactory
from unittest.mock import patch
from shop.models import Product
from shop.tests.factories import ProductFactory, CategoryFactory, ReviewFactory
from fakeredis import FakeRedis

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


class TestProductViewSet:
    def test_list_products(self, api_client):
        ProductFactory.create_batch(5)
        url = reverse("api-v1:product-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data["data"]) == 5

    @patch("shop.recommender.redis.from_url")
    def test_retrieve_product(self, mock_redis_from_url, api_client):
        mock_redis_from_url.return_value = FakeRedis()
        product = ProductFactory()
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["data"]["slug"] == product.slug

    def test_create_product(self, api_client):
        user = UserFactory(is_staff=True)
        category = CategoryFactory()
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:product-list")
        data = {
            "name": "Test Create",
            "description": "desc",
            "category": category.pk,
            "weight": "1.00",
            "length": "10.00",
            "width": "10.00",
            "height": "10.00",
        }
        response = api_client.post(url, data)
        assert response.status_code == 201
        assert response.data["data"]["name"] == "Test Create"


class TestCategoryViewSet:
    def test_list_categories(self, api_client):
        CategoryFactory.create_batch(3)
        url = reverse("api-v1:category-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data["data"]) == 3


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
        order = OrderFactory(user=user, status=Order.Status.PAID)
        OrderItemFactory(order=order, variant__product=product)
        api_client.force_authenticate(user=user)
        url = reverse(
            "api-v1:product-reviews-list", kwargs={"product_slug": product.slug}
        )
        response = api_client.post(url, {"rating": 4})
        assert response.status_code == 201
        assert response.data["rating"] == 4
