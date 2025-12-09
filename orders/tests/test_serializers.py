import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from shop.factories import ProductFactory, CategoryFactory
from account.factories import UserFactory, AddressFactory
from coupons.factories import CouponFactory
from orders.serializers import OrderCreateSerializer
from cart.cart import Cart

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def address(user):
    return AddressFactory(user=user)


@pytest.fixture
def product():
    return ProductFactory(stock=10, price=Decimal('100.00'))


from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

@pytest.fixture
def cart(product):
    # Create a mock request with a session to instantiate the cart
    request = RequestFactory().get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()

    cart_instance = Cart(request)
    cart_instance.add(product=product, quantity=2)
    # No need to save(), cart operations on session are synchronous
    return cart_instance


class TestOrderCreateSerializer:

    def test_create_order_successfully(self, user, address, product, cart):
        serializer_data = {
            'address_id': address.id,
            'coupon_code': None
        }

        context = {'request': type('Request', (), {'user': user, 'session': cart.session})}
        serializer = OrderCreateSerializer(data=serializer_data, context=context)

        assert serializer.is_valid(raise_exception=True)
        order = serializer.save()

        product.refresh_from_db()
        assert order.user == user
        assert order.address == address
        assert order.items.count() == 1
        assert order.items.first().product == product
        assert order.items.first().quantity == 2
        assert product.stock == 8  # Stock should be decremented

    def test_invalid_address_id_fails_validation(self, user, cart):
        invalid_address_id = 999
        serializer_data = {'address_id': invalid_address_id}
        context = {'request': type('Request', (), {'user': user, 'session': cart.session})}
        serializer = OrderCreateSerializer(data=serializer_data, context=context)

        with pytest.raises(ValidationError) as e:
            serializer.is_valid(raise_exception=True)
        assert 'address_id' in e.value.message_dict

    def test_order_out_of_stock_product_fails(self, user, address, cart):
        out_of_stock_product = ProductFactory(stock=0)
        cart.add(out_of_stock_product, 1)
        cart.save()

        serializer_data = {'address_id': address.id}
        context = {'request': type('Request', (), {'user': user, 'session': cart.session})}
        serializer = OrderCreateSerializer(data=serializer_data, context=context)

        with pytest.raises(ValidationError) as e:
            serializer.is_valid(raise_exception=True)
        assert 'stock' in str(e.value)

    def test_apply_valid_coupon_successfully(self, user, address, cart):
        coupon = CouponFactory(discount_percent=20)
        serializer_data = {
            'address_id': address.id,
            'coupon_code': coupon.code
        }

        context = {'request': type('Request', (), {'user': user, 'session': cart.session})}
        serializer = OrderCreateSerializer(data=serializer_data, context=context)

        assert serializer.is_valid(raise_exception=True)
        order = serializer.save()

        expected_total = Decimal('200.00')
        expected_discount = expected_total * (Decimal(coupon.discount_percent) / 100)

        assert order.coupon == coupon
        assert order.discount_amount == expected_discount
        assert order.total_price == expected_total - expected_discount

    def test_apply_invalid_coupon_is_ignored(self, user, address, cart):
        serializer_data = {
            'address_id': address.id,
            'coupon_code': 'INVALIDCODE'
        }

        context = {'request': type('Request', (), {'user': user, 'session': cart.session})}
        serializer = OrderCreateSerializer(data=serializer_data, context=context)

        # It should be valid, but the coupon validation logic should just find no coupon
        assert serializer.is_valid(raise_exception=True)
        order = serializer.save()

        assert order.coupon is None
        assert order.discount_amount == 0
        assert order.total_price == Decimal('200.00')
