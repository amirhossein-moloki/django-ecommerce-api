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
    return ProductFactory(name='Product A', variants=[{'price': Decimal('10.00'), 'stock': 10}])

@pytest.fixture
def variant_a(product_a):
    return product_a.variants.first()

@pytest.fixture
def product_b():
    return ProductFactory(name='Product B', variants=[{'price': Decimal('25.00'), 'stock': 10}])

@pytest.fixture
def variant_b(product_b):
    return product_b.variants.first()


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

    def test_add_to_cart_anonymous(self, anonymous_request, variant_a):
        cart = Cart(anonymous_request)
        cart.add(variant=variant_a, quantity=2)

        assert str(variant_a.variant_id) in cart.cart
        assert cart.cart[str(variant_a.variant_id)]['quantity'] == 2
        assert len(cart) == 2

    def test_add_to_cart_authenticated(self, authenticated_request, variant_a):
        cart = Cart(authenticated_request)
        cart.add(variant=variant_a, quantity=3)

        db_cart = DbCart.objects.get(user=authenticated_request.user)
        cart_item = CartItem.objects.get(cart=db_cart, variant=variant_a)

        assert cart_item.quantity == 3
        assert len(cart) == 3

    def test_clear_cart_anonymous(self, anonymous_request, variant_a):
        cart = Cart(anonymous_request)
        cart.add(variant_a, 1)
        assert 'cart' in anonymous_request.session

        cart.clear()
        assert 'cart' not in anonymous_request.session

    def test_clear_cart_authenticated(self, authenticated_request, variant_a):
        cart = Cart(authenticated_request)
        cart.add(variant_a, 1)
        assert DbCart.objects.filter(user=authenticated_request.user).exists()

        cart.clear()
        assert not DbCart.objects.filter(user=authenticated_request.user).exists()

    def test_get_total_price_after_discount(self, anonymous_request, variant_a, variant_b):
        cart = Cart(anonymous_request)
        cart.add(variant_a, 2)  # 2 * 10 = 20
        cart.add(variant_b, 1)  # 1 * 25 = 25
        # Total price = 45

        coupon = CouponFactory(discount_percent=10) # 10% discount = 4.5
        cart.coupon = coupon
        cart.save()


        assert cart.get_total_price_after_discount() == Decimal('40.50')

    def test_merge_session_cart_on_login(self, anonymous_request, user, variant_a, variant_b):
        # 1. Anonymous user adds items to session cart
        session_cart = Cart(anonymous_request)
        session_cart.add(variant_a, quantity=1)
        session_cart.add(variant_b, quantity=2) # Total 3 items

        # 2. User logs in. Create a new request object for the authenticated user
        auth_request = RequestFactory().get('/')
        auth_request.session = anonymous_request.session # CRITICAL: Carry over the session
        auth_request.user = user

        # 3. Authenticated user already has an item in their DB cart
        db_cart = DbCart.objects.create(user=user)
        CartItem.objects.create(cart=db_cart, variant=variant_b, quantity=1)

        # 4. Instantiate the cart for the authenticated user, which should trigger the merge
        final_cart = Cart(auth_request)

        # 5. Verify the merge logic
        # - The session cart should be cleared
        assert 'cart' not in final_cart.session

        # - The DB cart should be updated
        # - variant_a (only in session) should be added
        item_a = CartItem.objects.get(cart=db_cart, variant=variant_a)
        assert item_a.quantity == 1

        # - variant_b (in both) should have quantities summed (2 from session + 1 from db)
        item_b = CartItem.objects.get(cart=db_cart, variant=variant_b)
        assert item_b.quantity == 3

        # - Total items in cart should be 1 + 3 = 4
        assert len(final_cart) == 4
