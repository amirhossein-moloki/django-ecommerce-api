import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from account.tests.factories import UserFactory
from orders.models import Order
from orders.tests.factories import OrderFactory, OrderItemFactory
from shop.models import Product
from shop.tests.factories import ProductFactory, CategoryFactory, ReviewFactory

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
        assert response.data["count"] == 5

    def test_retrieve_product(self, api_client):
        product = ProductFactory()
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["slug"] == product.slug

    def test_create_product(self, api_client):
        user = UserFactory()
        category = CategoryFactory()
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:product-list")
        data = {
            "name": "Test Create",
            "description": "desc",
            "category": category.pk,
            "weight": 1,
        }
        response = api_client.post(url, data)
        assert response.status_code == 201
        assert response.data["name"] == "Test Create"


class TestCategoryViewSet:
    def test_list_categories(self, api_client):
        CategoryFactory.create_batch(3)
        url = reverse("api-v1:category-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 3


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
