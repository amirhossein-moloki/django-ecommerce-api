import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from shop.factories import ProductFactory, CategoryFactory
from account.factories import UserFactory, AdminUserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def category():
    return CategoryFactory()


class TestProductViewSetPermissions:

    def test_owner_can_update_their_product(self, api_client, category):
        owner = UserFactory()
        product = ProductFactory(user=owner, category=category)
        api_client.force_authenticate(user=owner)

        url = reverse('api-v1:shop:products-detail', kwargs={'slug': product.slug})
        data = {'name': 'Updated Name', 'price': 150.00}
        response = api_client.patch(url, data)

        product.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert product.name == 'Updated Name'

    def test_non_owner_cannot_update_product(self, api_client, category):
        owner = UserFactory()
        other_user = UserFactory()
        product = ProductFactory(user=owner, category=category, name='Original Name')
        api_client.force_authenticate(user=other_user)

        url = reverse('api-v1:shop:products-detail', kwargs={'slug': product.slug})
        data = {'name': 'Updated Name'}
        response = api_client.patch(url, data)

        product.refresh_from_db()
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert product.name == 'Original Name'

    def test_admin_can_update_any_product(self, api_client, category):
        owner = UserFactory()
        admin = AdminUserFactory()
        product = ProductFactory(user=owner, category=category)
        api_client.force_authenticate(user=admin)

        url = reverse('api-v1:shop:products-detail', kwargs={'slug': product.slug})
        data = {'name': 'Admin Updated Name'}
        response = api_client.patch(url, data)

        product.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert product.name == 'Admin Updated Name'

    def test_owner_can_delete_their_product(self, api_client, category):
        owner = UserFactory()
        product = ProductFactory(user=owner, category=category)
        api_client.force_authenticate(user=owner)

        url = reverse('api-v1:shop:products-detail', kwargs={'slug': product.slug})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        with pytest.raises(type(product).DoesNotExist):
            product.refresh_from_db()

    def test_non_owner_cannot_delete_product(self, api_client, category):
        owner = UserFactory()
        other_user = UserFactory()
        product = ProductFactory(user=owner, category=category)
        api_client.force_authenticate(user=other_user)

        url = reverse('api-v1:shop:products-detail', kwargs={'slug': product.slug})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert type(product).objects.filter(pk=product.pk).exists()

    def test_admin_can_delete_any_product(self, api_client, category):
        owner = UserFactory()
        admin = AdminUserFactory()
        product = ProductFactory(user=owner, category=category)
        api_client.force_authenticate(user=admin)

        url = reverse('api-v1:shop:products-detail', kwargs={'slug': product.slug})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        with pytest.raises(type(product).DoesNotExist):
            product.refresh_from_db()
