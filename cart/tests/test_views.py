import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from .factories import UserFactory, ProductVariantFactory
from cart.models import Cart, CartItem

pytestmark = pytest.mark.django_db


class TestCartAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.variant1 = ProductVariantFactory(stock=10)
        self.variant2 = ProductVariantFactory(stock=5)

    # --- Authenticated User API Tests ---

    def test_get_cart_authenticated_user_empty(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("api-v1:cart-list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["items"] == []
        assert response.data["total_price"]["with_discount"] == 0

    def test_get_cart_authenticated_user_with_items(self):
        # Setup cart directly using models
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant1, quantity=2)

        self.client.force_authenticate(user=self.user)
        url = reverse("api-v1:cart-list")
        response = self.client.get(url)

        assert response.status_code == 200
        assert len(response.data["items"]) == 1
        assert response.data["items"][0]["quantity"] == 2
        assert response.data["items"][0]["variant"]["variant_id"] == str(
            self.variant1.variant_id
        )
        assert float(response.data["total_price"]["with_discount"]) == float(
            self.variant1.price * 2
        )

    def test_add_to_cart_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "api-v1:cart-add", kwargs={"variant_id": self.variant1.variant_id}
        )
        payload = {"quantity": 3}
        response = self.client.post(url, payload)

        assert response.status_code == 200
        assert response.data["message"] == "Product added/updated in cart"
        assert (
            Cart.objects.get(user=self.user).items.get(variant=self.variant1).quantity
            == 3
        )

    def test_add_to_cart_invalid_variant_id(self):
        import uuid

        self.client.force_authenticate(user=self.user)
        url = reverse("api-v1:cart-add", kwargs={"variant_id": uuid.uuid4()})
        response = self.client.post(url, {"quantity": 1})

        assert response.status_code == 404
        assert response.data["message"] == "Product not found."

    def test_remove_from_cart_authenticated_user(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant1, quantity=1)

        self.client.force_authenticate(user=self.user)
        url = reverse(
            "api-v1:cart-remove", kwargs={"variant_id": self.variant1.variant_id}
        )
        response = self.client.delete(url)

        assert response.status_code == 200
        assert response.data["message"] == "Product removed from cart"
        assert (
            not Cart.objects.get(user=self.user)
            .items.filter(variant=self.variant1)
            .exists()
        )

    def test_clear_cart_authenticated_user(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant1, quantity=1)

        self.client.force_authenticate(user=self.user)
        url = reverse("api-v1:cart-clear")
        response = self.client.delete(url)

        assert response.status_code == 204
        assert not Cart.objects.filter(user=self.user).exists()

    # --- Guest User API Tests ---

    def test_get_cart_guest_user(self):
        # First request creates the cart
        url = reverse("api-v1:cart-list")
        response1 = self.client.get(url)
        assert response1.status_code == 200
        assert response1.data["items"] == []

        # Get the session key to simulate subsequent requests
        session_key = self.client.session.session_key
        assert session_key is not None

        # Second request should return the same cart
        response2 = self.client.get(url)
        assert response2.status_code == 200
        assert self.client.session.session_key == session_key

    def test_add_to_cart_guest_user(self):
        url = reverse(
            "api-v1:cart-add", kwargs={"variant_id": self.variant1.variant_id}
        )
        response = self.client.post(url, {"quantity": 2})

        assert response.status_code == 200
        session_key = self.client.session.session_key
        cart = Cart.objects.get(session_key=session_key)
        assert cart.items.get(variant=self.variant1).quantity == 2

    def test_api_cart_merges_on_login(self):
        # 1. Guest adds an item
        add_url = reverse(
            "api-v1:cart-add", kwargs={"variant_id": self.variant1.variant_id}
        )
        self.client.post(add_url, {"quantity": 1})
        guest_session_key = self.client.session.session_key

        # 2. User logs in (the client now carries the session)
        self.client.force_authenticate(user=self.user)

        # 3. Get the cart. The Cart.__init__ logic should be triggered by the request
        get_url = reverse("api-v1:cart-list")
        response = self.client.get(get_url)

        assert response.status_code == 200
        # Guest cart is deleted
        assert not Cart.objects.filter(session_key=guest_session_key).exists()
        # Item is now in the user's cart
        user_cart = Cart.objects.get(user=self.user)
        assert user_cart.items.get(variant=self.variant1).quantity == 1
        assert len(response.data["items"]) == 1
