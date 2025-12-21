import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from shop.factories import ProductFactory, CategoryFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def category1():
    return CategoryFactory(name='Electronics')


@pytest.fixture
def category2():
    return CategoryFactory(name='Books')


@pytest.fixture
def product1(category1, user):
    p = ProductFactory(
        name='Laptop', description='A powerful laptop for programming',
        category=category1, user=user, price='1200.00', stock=10
    )
    p.tags.add('tech', 'computers')
    return p


@pytest.fixture
def product2(category1, user):
    p = ProductFactory(
        name='Smartphone', description='A modern smartphone with a great camera',
        category=category1, user=user, price='800.00', stock=5
    )
    p.tags.add('tech', 'mobile')
    return p


@pytest.fixture
def product3(category2, user):
    p = ProductFactory(
        name='Python Crash Course', description='A book about Python programming',
        category=category2, user=user, price='30.00', stock=0
    )
    p.tags.add('programming', 'python', 'books')
    return p


@pytest.fixture
def product4(category2, user):
    p = ProductFactory(
        name='The Pragmatic Programmer', description='A book about the art of programming',
        category=category2, user=user, price='45.00', stock=20
    )
    p.tags.add('programming', 'software', 'books')
    return p


@pytest.fixture
def url():
    return reverse('api-v1:product-list')


def test_filter_by_name_exact(api_client, url, product1, product2, product3, product4):
    response = api_client.get(url, {'name': 'Laptop'})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['name'] == 'Laptop'


def test_filter_by_price_range(api_client, url, product1, product2, product3, product4):
    response = api_client.get(url, {'variants__price__range': '700,1300'})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 2


def test_filter_by_category_slug(api_client, url, product1, product2, product3, product4):
    response = api_client.get(url, {'category__slug': 'electronics'})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 2


def test_filter_by_tags_name(api_client, url, product1, product2, product3, product4):
    response = api_client.get(url, {'tags__name__in': 'tech'})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 2

def test_in_stock_filter_backend(api_client, url, product1, product2, product3, product4):
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    # product3 is out of stock
    assert len(response.data['results']) == 3


def test_ordering_by_price_ascending(api_client, url, product1, product2, product3, product4):
    response = api_client.get(url, {'ordering': 'min_price'})
    assert response.status_code == status.HTTP_200_OK
    prices = [item['variants'][0]['price'] for item in response.data['results']]
    # product3 is out of stock
    assert prices == ['45.00', '800.00', '1200.00']
