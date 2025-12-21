import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from shop.factories import ProductFactory, CategoryFactory
from account.factories import UserFactory
from cart.models import Cart, CartItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(api_client):
    user = UserFactory()
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def category():
    return CategoryFactory()


@pytest.fixture
def product(category):
    return ProductFactory(
        category=category,
        price=Decimal("10.00"),
        stock=10
    )


@pytest.mark.django_db
class TestCartAPI:
    def test_add_to_cart(self, api_client, user, product):
        url = reverse('api-v1:cart-add', kwargs={'product_id': product.product_id})
        response = api_client.post(url, {'quantity': 2}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Product added/updated in cart'

        cart = Cart.objects.get(user=user)
        cart_item = CartItem.objects.get(cart=cart, product=product)
        assert cart_item.quantity == 2

    def test_add_to_cart_quantity_limit(self, api_client, user, product):
        url = reverse('api-v1:cart-add', kwargs={'product_id': product.product_id})
        response = api_client.post(url, {'quantity': 51}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Cannot add more than 50 items' in response.data['quantity'][0]

    def test_add_to_cart_out_of_stock(self, api_client, user, product):
        product.stock = 0
        product.save()

        url = reverse('api-v1:cart-add', kwargs={'product_id': product.product_id})
        response = api_client.post(url, {'quantity': 1}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == 'This product is out of stock.'

    def test_add_to_cart_insufficient_stock(self, api_client, user, product):
        url = reverse('api-v1:cart-add', kwargs={'product_id': product.product_id})
        response = api_client.post(url, {'quantity': 11}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Only 10 more items can be added' in response.data['error']

    def test_remove_from_cart(self, api_client, user, product):
        # First, add the product to the cart
        add_url = reverse('api-v1:cart-add', kwargs={'product_id': product.product_id})
        api_client.post(add_url, {'quantity': 1}, format='json')

        # Then, remove it
        remove_url = reverse('api-v1:cart-remove', kwargs={'product_id': product.product_id})
        response = api_client.delete(remove_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Product removed from cart'

        cart = Cart.objects.get(user=user)
        assert not CartItem.objects.filter(cart=cart, product=product).exists()

    def test_remove_non_existent_product_from_cart(self, api_client, user):
        import uuid
        non_existent_product_id = uuid.uuid4()
        remove_url = reverse('api-v1:cart-remove', kwargs={'product_id': non_existent_product_id})
        response = api_client.delete(remove_url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == 'Product not found.'

    def test_clear_cart(self, api_client, user, product):
        # First, add the product to the cart
        add_url = reverse('api-v1:cart-add', kwargs={'product_id': product.product_id})
        api_client.post(add_url, {'quantity': 1}, format='json')

        # Then, clear the cart
        clear_url = reverse('api-v1:cart-clear')
        response = api_client.delete(clear_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        cart = Cart.objects.get(user=user)
        assert not CartItem.objects.filter(cart=cart).exists()
