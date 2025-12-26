import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from cart.cart import Cart
from cart.models import Cart as CartModel, CartItem
from .factories import UserFactory, ProductVariantFactory

pytestmark = pytest.mark.django_db


class TestCartService:
    def setup_method(self):
        self.request_factory = RequestFactory()
        self.user = UserFactory()
        self.variant1 = ProductVariantFactory(stock=10)
        self.variant2 = ProductVariantFactory(stock=5)

    def _get_request_with_session(self, user=None):
        request = self.request_factory.get("/")
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = user or self.user
        return request

    def test_add_item_authenticated_user_new_item(self):
        request = self._get_request_with_session()
        cart = Cart(request)
        assert len(cart) == 0

        cart.add(variant=self.variant1, quantity=2)

        assert len(cart) == 2
        cart_db = CartModel.objects.get(user=self.user)
        assert cart_db.items.count() == 1
        cart_item = cart_db.items.first()
        assert cart_item.variant == self.variant1
        assert cart_item.quantity == 2

    def test_add_item_authenticated_user_existing_item(self):
        request = self._get_request_with_session()
        cart = Cart(request)
        cart.add(variant=self.variant1, quantity=1)
        assert len(cart) == 1

        cart.add(variant=self.variant1, quantity=3)
        assert len(cart) == 4
        cart_db = CartModel.objects.get(user=self.user)
        assert cart_db.items.count() == 1
        cart_item = cart_db.items.first()
        assert cart_item.quantity == 4

    def test_add_item_override_quantity(self):
        request = self._get_request_with_session()
        cart = Cart(request)
        cart.add(variant=self.variant1, quantity=1)
        assert len(cart) == 1

        cart.add(variant=self.variant1, quantity=3, override_quantity=True)
        assert len(cart) == 3
        cart_item = CartItem.objects.get(cart__user=self.user, variant=self.variant1)
        assert cart_item.quantity == 3

    def test_remove_item_authenticated_user(self):
        request = self._get_request_with_session()
        cart = Cart(request)
        cart.add(variant=self.variant1, quantity=2)
        cart.add(variant=self.variant2, quantity=1)
        assert len(cart) == 3

        cart.remove(variant=self.variant1)
        assert len(cart) == 1
        cart_db = CartModel.objects.get(user=self.user)
        assert cart_db.items.count() == 1
        assert not cart_db.items.filter(variant=self.variant1).exists()

    def test_clear_cart_authenticated_user(self):
        request = self._get_request_with_session()
        cart = Cart(request)
        cart.add(variant=self.variant1)
        cart.add(variant=self.variant2)
        assert CartModel.objects.filter(user=self.user).exists()

        cart.clear()

        assert not CartModel.objects.filter(user=self.user).exists()
        assert not request.session.get('cart_session_id')

    def test_get_total_price(self):
        request = self._get_request_with_session()
        cart = Cart(request)
        cart.add(self.variant1, quantity=2) # price * 2
        cart.add(self.variant2, quantity=3) # price * 3

        expected_total = (self.variant1.price * 2) + (self.variant2.price * 3)
        assert cart.get_total_price() == expected_total

    # --- Guest User Scenarios ---

    def test_add_item_guest_user(self):
        request = self._get_request_with_session(user=AnonymousUser())
        cart = Cart(request)
        assert cart.cart.user is None
        assert cart.cart.session_key is not None

        cart.add(variant=self.variant1, quantity=1)

        assert len(cart) == 1
        session_key = request.session.session_key
        cart_db = CartModel.objects.get(session_key=session_key)
        assert cart_db.items.count() == 1
        assert cart_db.items.first().quantity == 1

    def test_cart_persists_for_guest_user_across_requests(self):
        request1 = self._get_request_with_session(user=AnonymousUser())
        cart1 = Cart(request1)
        cart1.add(self.variant1)

        session_key = request1.session.session_key

        request2 = self.request_factory.get("/")
        request2.session = request1.session # Simulate same browser session
        request2.user = AnonymousUser()

        cart2 = Cart(request2)
        assert len(cart2) == 1
        assert cart2.cart.session_key == session_key

    # --- Cart Merging Scenario ---

    def test_merge_guest_cart_on_login(self):
        # 1. Create a cart as a guest
        guest_request = self._get_request_with_session(user=AnonymousUser())
        guest_cart = Cart(guest_request)
        guest_cart.add(self.variant1, quantity=2)
        guest_cart.add(self.variant2, quantity=1)
        guest_session_key = guest_request.session.session_key

        assert CartModel.objects.filter(session_key=guest_session_key).exists()

        # 2. Authenticate the user and simulate a new request (login)
        # The new request will have the same session as the guest
        login_request = self.request_factory.get("/")
        login_request.session = guest_request.session
        login_request.user = self.user

        # 3. Initialize the cart for the logged-in user
        # This should trigger the merge logic in Cart.__init__
        user_cart = Cart(login_request)

        # 4. Assertions
        # - The guest cart should be deleted
        assert not CartModel.objects.filter(session_key=guest_session_key).exists()

        # - The user's cart should now contain the items from the guest cart
        user_cart_db = CartModel.objects.get(user=self.user)
        assert user_cart_db.items.count() == 2
        assert len(user_cart) == 3

        item1 = user_cart_db.items.get(variant=self.variant1)
        assert item1.quantity == 2

        item2 = user_cart_db.items.get(variant=self.variant2)
        assert item2.quantity == 1

        # - The session key should be cleared from the session
        assert login_request.session.get('cart_session_id') is None

    def test_merge_guest_cart_with_existing_user_cart(self):
        # 1. User already has items in their cart
        user_request = self._get_request_with_session()
        user_cart = Cart(user_request)
        user_cart.add(self.variant1, quantity=1) # User has 1 of variant1

        # 2. The same user browses as a guest and adds items
        guest_request = self._get_request_with_session(user=AnonymousUser())
        guest_cart = Cart(guest_request)
        guest_cart.add(self.variant1, quantity=2) # Guest adds 2 of variant1
        guest_cart.add(self.variant2, quantity=3) # Guest adds 3 of variant2

        # 3. User logs in with the guest session
        login_request = self.request_factory.get("/")
        login_request.session = guest_request.session
        login_request.user = self.user

        final_cart = Cart(login_request)

        # 4. Assertions: Quantities should be combined
        assert len(final_cart) == 1 + 2 + 3 # 6 items total
        user_cart_db = CartModel.objects.get(user=self.user)
        assert user_cart_db.items.count() == 2

        item1 = user_cart_db.items.get(variant=self.variant1)
        assert item1.quantity == 3 # 1 (user) + 2 (guest)

        item2 = user_cart_db.items.get(variant=self.variant2)
        assert item2.quantity == 3 # 0 (user) + 3 (guest)

    # --- Validation from services.py ---
    # Although validation is in services, we test the interaction via Cart class
    # for a more integrated test of the business logic.

    def test_add_to_cart_service_out_of_stock(self):
        from cart.services import add_to_cart
        from rest_framework.exceptions import ValidationError

        out_of_stock_variant = ProductVariantFactory(stock=0)
        request = self._get_request_with_session()

        with pytest.raises(ValidationError, match="This product is out of stock."):
            add_to_cart(request, out_of_stock_variant.variant_id)

    def test_add_to_cart_service_insufficient_stock(self):
        from cart.services import add_to_cart
        from rest_framework.exceptions import ValidationError

        request = self._get_request_with_session()
        # variant1 has stock of 10
        cart = Cart(request)
        cart.add(self.variant1, quantity=8)

        with pytest.raises(ValidationError, match="Cannot add 3 items. Only 2 more items can be added."):
            add_to_cart(request, self.variant1.variant_id, quantity=3)

        # Test adding without override
        add_to_cart(request, self.variant1.variant_id, quantity=2)
        assert len(cart) == 10

        # Now try to add more
        with pytest.raises(ValidationError, match="Cannot add 1 items. Only 0 more items can be added."):
            add_to_cart(request, self.variant1.variant_id, quantity=1)
