import pytest
from decimal import Decimal
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser

from cart.cart import Cart
from cart.models import Cart as DbCart, CartItem
from shop.factories import ProductFactory
from account.factories import UserFactory
from coupons.factories import CouponFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def product_a():
    return ProductFactory(name='Product A', price=Decimal('10.00'), stock=10)


@pytest.fixture
def product_b():
    return ProductFactory(name='Product B', price=Decimal('25.00'), stock=10)


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def anonymous_request():
    """Creates a mock request for an anonymous user with a session."""
    request = RequestFactory().get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    request.user = AnonymousUser()
    return request


@pytest.fixture
def authenticated_request(user):
    """Creates a mock request for an authenticated user with a session."""
    request = RequestFactory().get('/')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    request.user = user
    return request


class TestCartLogic:

    def test_add_to_cart_anonymous(self, anonymous_request, product_a):
        cart = Cart(anonymous_request)
        cart.add(product=product_a, quantity=2)

        assert str(product_a.product_id) in cart.session['cart']
        assert cart.session['cart'][str(product_a.product_id)]['quantity'] == 2
        assert len(cart) == 2

    def test_add_to_cart_authenticated(self, authenticated_request, product_a):
        cart = Cart(authenticated_request)
        cart.add(product=product_a, quantity=3)

        db_cart = DbCart.objects.get(user=authenticated_request.user)
        cart_item = CartItem.objects.get(cart=db_cart, product=product_a)

        assert cart_item.quantity == 3
        assert len(cart) == 3

    def test_clear_cart_anonymous(self, anonymous_request, product_a):
        cart = Cart(anonymous_request)
        cart.add(product_a, 1)
        assert 'cart' in anonymous_request.session

        cart.clear()
        assert 'cart' not in anonymous_request.session

    def test_clear_cart_authenticated(self, authenticated_request, product_a):
        cart = Cart(authenticated_request)
        cart.add(product_a, 1)
        assert DbCart.objects.filter(user=authenticated_request.user).exists()

        cart.clear()
        assert not DbCart.objects.filter(user=authenticated_request.user).exists()

    def test_get_total_price_after_discount(self, anonymous_request, product_a, product_b):
        cart = Cart(anonymous_request)
        cart.add(product_a, 2)  # 2 * 10 = 20
        cart.add(product_b, 1)  # 1 * 25 = 25
        # Total price = 45

        coupon = CouponFactory(discount_percent=10) # 10% discount = 4.5
        anonymous_request.session['coupon_id'] = coupon.id
        anonymous_request.session.save()

        cart_with_coupon = Cart(anonymous_request)
        assert cart_with_coupon.get_total_price_after_discount() == Decimal('40.50')

    def test_merge_session_cart_on_login(self, anonymous_request, user, product_a, product_b):
        # 1. Anonymous user adds items to session cart
        session_cart = Cart(anonymous_request)
        session_cart.add(product_a, quantity=1)
        session_cart.add(product_b, quantity=2) # Total 3 items

        # 2. User logs in. Create a new request object for the authenticated user
        auth_request = RequestFactory().get('/')
        auth_request.session = anonymous_request.session # CRITICAL: Carry over the session
        auth_request.user = user

        # 3. Authenticated user already has an item in their DB cart
        db_cart = DbCart.objects.create(user=user)
        CartItem.objects.create(cart=db_cart, product=product_b, quantity=1)

        # 4. Instantiate the cart for the authenticated user, which should trigger the merge
        final_cart = Cart(auth_request)

        # 5. Verify the merge logic
        # - The session cart should be cleared
        assert 'cart' not in final_cart.session

        # - The DB cart should be updated
        # - product_a (only in session) should be added
        item_a = CartItem.objects.get(cart=db_cart, product=product_a)
        assert item_a.quantity == 1

        # - product_b (in both) should have quantities summed (2 from session + 1 from db)
        item_b = CartItem.objects.get(cart=db_cart, product=product_b)
        assert item_b.quantity == 3

        # - Total items in cart should be 1 + 3 = 4
        assert len(final_cart) == 4
