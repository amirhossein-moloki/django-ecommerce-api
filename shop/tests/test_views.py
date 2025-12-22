import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from shop.factories import CategoryFactory, ProductFactory, ReviewFactory, UserFactory
from orders.factories import OrderFactory, OrderItemFactory

pytestmark = pytest.mark.django_db


class TestCategoryViewSet:
    def test_list_categories(self, api_client):
        CategoryFactory.create_batch(3)
        url = reverse('api-v1:category-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_retrieve_category(self, api_client):
        category = CategoryFactory()
        url = reverse('api-v1:category-detail', kwargs={'slug': category.slug})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == category.name

    def test_create_category_permission(self, api_client, user):
        api_client.force_authenticate(user=user)
        url = reverse('api-v1:category-list')
        data = {'name': 'New Category'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_category_admin(self, admin_api_client):
        url = reverse('api-v1:category-list')
        data = {'name': 'New Category'}
        response = admin_api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED


class TestProductViewSet:
    def test_list_products(self, api_client):
        ProductFactory.create_batch(3)
        url = reverse('api-v1:product-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    @patch('shop.recommender.Recommender.suggest_products_for')
    def test_retrieve_product(self, mock_suggest, api_client):
        mock_suggest.return_value = []
        product = ProductFactory()
        url = reverse('api-v1:product-detail', kwargs={'slug': product.slug})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == product.name

    def test_create_product(self, api_client, user):
        api_client.force_authenticate(user=user)
        category = CategoryFactory()
        url = reverse('api-v1:product-list')
        data = {
            'name': 'New Product',
            'description': 'A new product',
            'category_slug': category.slug,
            'variants': [{'price': '20.00', 'stock': 10, 'sku': 'NP001'}]
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_product_by_owner(self, api_client, user):
        api_client.force_authenticate(user=user)
        product = ProductFactory(user=user)
        url = reverse('api-v1:product-detail', kwargs={'slug': product.slug})
        data = {'name': 'Updated Product'}
        response = api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.name == 'Updated Product'


class TestReviewViewSet:
    def test_list_reviews(self, api_client):
        product = ProductFactory()
        ReviewFactory.create_batch(3, product=product)
        url = reverse('api-v1:product-reviews-list', kwargs={'product_slug': product.slug})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_create_review_by_purchaser(self, api_client, user):
        api_client.force_authenticate(user=user)
        product = ProductFactory()
        variant = product.variants.first()
        order = OrderFactory(user=user, status='paid')
        OrderItemFactory(order=order, variant=variant)
        url = reverse('api-v1:product-reviews-list', kwargs={'product_slug': product.slug})
        data = {'rating': 4, 'comment': 'Good product.'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_review_by_non_purchaser(self, api_client, user):
        api_client.force_authenticate(user=user)
        product = ProductFactory()
        url = reverse('api-v1:product-reviews-list', kwargs={'product_slug': product.slug})
        data = {'rating': 3, 'comment': 'I dont know.'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
