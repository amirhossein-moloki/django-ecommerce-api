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
    def test_list_products_unauthenticated(self, api_client):
        """
        Tests that unauthenticated users can list products.
        """
        ProductFactory.create_batch(5)
        url = reverse("api-v1:product-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 5

    def test_retrieve_product_unauthenticated(self, api_client):
        """
        Tests that unauthenticated users can retrieve a single product.
        """
        product = ProductFactory()
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["slug"] == product.slug

    def test_create_product_authenticated(self, api_client):
        """
        Tests that authenticated users can create products.
        """
        user = UserFactory()
        category = CategoryFactory()
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:product-list")
        data = {
            "name": "New Test Product",
            "description": "A great product",
            "category": category.pk,
            "tags": "new,test",
            "weight": 1.5,
        }
        response = api_client.post(url, data)
        assert response.status_code == 201
        assert response.data["name"] == "New Test Product"
        # In the actual serializer, the user object is returned, not just the username.
        # So we check for the user's ID.
        assert response.data["user"]["id"] == user.id

    def test_create_product_unauthenticated(self, api_client):
        """
        Tests that unauthenticated users cannot create products.
        """
        category = CategoryFactory()
        url = reverse("api-v1:product-list")
        data = {"name": "Forbidden Product", "category": category.pk}
        response = api_client.post(url, data)
        assert response.status_code == 401

    def test_update_product_by_owner(self, api_client):
        """
        Tests that the product owner can update their product.
        """
        user = UserFactory()
        product = ProductFactory(user=user)
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        data = {"name": "Updated Name"}
        response = api_client.patch(url, data)
        assert response.status_code == 200
        assert response.data["name"] == "Updated Name"

    def test_update_product_by_non_owner(self, api_client):
        """
        Tests that a user who is not the owner cannot update the product.
        """
        user1 = UserFactory()
        user2 = UserFactory()
        product = ProductFactory(user=user1)
        api_client.force_authenticate(user=user2)
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        data = {"name": "Should Not Update"}
        response = api_client.patch(url, data)
        assert response.status_code == 403

    def test_delete_product_by_owner(self, api_client):
        """
        Tests that the product owner can delete their product.
        """
        user = UserFactory()
        product = ProductFactory(user=user)
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:product-detail", kwargs={"slug": product.slug})
        response = api_client.delete(url)
        assert response.status_code == 204
        assert not Product.objects.filter(pk=product.pk).exists()


    def test_product_filtering_by_category(self, api_client):
        """
        Tests filtering products by category slug.
        """
        cat1 = CategoryFactory(name="Electronics")
        cat2 = CategoryFactory(name="Books")
        ProductFactory.create_batch(3, category=cat1)
        ProductFactory.create_batch(2, category=cat2)

        url = f'{reverse("api-v1:product-list")}?category__slug={cat1.slug}'
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 3


class TestReviewViewSet:
    def test_create_review_unauthenticated(self, api_client):
        """
        Tests that unauthenticated users cannot create a review.
        """
        product = ProductFactory()
        url = reverse("api-v1:product-reviews-list", kwargs={"product_slug": product.slug})
        data = {"rating": 5, "comment": "This is a test comment"}
        response = api_client.post(url, data)
        assert response.status_code == 401

    def test_create_review_without_purchase(self, api_client):
        """
        Tests that a user who has not purchased the product cannot create a review.
        """
        user = UserFactory()
        product = ProductFactory()
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:product-reviews-list", kwargs={"product_slug": product.slug})
        data = {"rating": 5, "comment": "I never bought this"}
        response = api_client.post(url, data)
        assert response.status_code == 403

    def test_create_review_with_purchase(self, api_client):
        """
        Tests that a user who has purchased the product can create a review.
        """
        user = UserFactory()
        product = ProductFactory()
        order = OrderFactory(user=user, status=Order.Status.PAID)
        OrderItemFactory(order=order, variant__product=product)

        api_client.force_authenticate(user=user)
        url = reverse("api-v1:product-reviews-list", kwargs={"product_slug": product.slug})
        data = {"rating": 4, "comment": "It was pretty good"}
        response = api_client.post(url, data)
        assert response.status_code == 201
        assert response.data["rating"] == 4

    def test_update_review_by_owner(self, api_client):
        """
        Tests that the review owner can update their review.
        """
        user = UserFactory()
        review = ReviewFactory(user=user)
        api_client.force_authenticate(user=user)
        url = reverse(
            "api-v1:product-reviews-detail",
            kwargs={"product_slug": review.product.slug, "pk": review.pk},
        )
        data = {"comment": "An updated comment"}
        response = api_client.patch(url, data)
        assert response.status_code == 200
        assert response.data["comment"] == "An updated comment"


class TestCategoryViewSet:
    def test_list_categories_unauthenticated(self, api_client):
        """
        Tests that unauthenticated users can list categories.
        """
        CategoryFactory.create_batch(3)
        url = reverse("api-v1:category-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert len(response.data["results"]) == 3

    def test_create_category_as_admin(self, api_client):
        """
        Tests that admin users can create categories.
        """
        admin_user = UserFactory(is_staff=True)
        api_client.force_authenticate(user=admin_user)
        url = reverse("api-v1:category-list")
        data = {"name": "New Admin Category"}
        response = api_client.post(url, data)
        assert response.status_code == 201

    def test_create_category_as_normal_user(self, api_client):
        """
        Tests that normal users cannot create categories.
        """
        user = UserFactory()
        api_client.force_authenticate(user=user)
        url = reverse("api-v1:category-list")
        data = {"name": "Forbidden Category"}
        response = api_client.post(url, data)
        assert response.status_code == 403
