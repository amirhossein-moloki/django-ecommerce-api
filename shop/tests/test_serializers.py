import pytest
from shop.serializers import ProductSerializer
from shop.factories import CategoryFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    return CategoryFactory(slug='test-category')


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def valid_data(category):
    return {
        'name': 'New Product',
        'description': 'A valid description',
        'category_slug': category.slug,
        'variants': [
            {'price': '25.50', 'stock': 100, 'sku': 'NP001-S'},
            {'price': '27.50', 'stock': 50, 'sku': 'NP001-M'},
        ]
    }


def test_product_serializer_valid_data(valid_data, user):
    serializer = ProductSerializer(data=valid_data, context={'user': user})
    assert serializer.is_valid(), serializer.errors


def test_product_serializer_name_is_required(valid_data):
    data = valid_data.copy()
    data.pop('name')
    serializer = ProductSerializer(data=data)
    assert not serializer.is_valid()
    assert 'name' in serializer.errors


def test_product_serializer_variants_must_be_a_list(valid_data):
    data = valid_data.copy()
    data['variants'] = {'price': '25.50', 'stock': 100}
    serializer = ProductSerializer(data=data)
    assert not serializer.is_valid()
    assert 'variants' in serializer.errors


def test_variant_serializer_price_must_be_positive(valid_data):
    data = valid_data.copy()
    data['variants'][0]['price'] = '-10.00'
    serializer = ProductSerializer(data=data)
    assert not serializer.is_valid()
    assert 'price' in serializer.errors['variants'][0]


def test_variant_serializer_stock_must_be_non_negative(valid_data):
    data = valid_data.copy()
    data['variants'][0]['stock'] = -1
    serializer = ProductSerializer(data=data)
    assert not serializer.is_valid()
    assert 'stock' in serializer.errors['variants'][0]
