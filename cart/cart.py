from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404

from coupons.models import Coupon
from shop.models import Product
from .models import Cart as CartModel, CartItem


class Cart:
    """
    A unified, database-backed cart class that handles both anonymous
    and authenticated users.
    """

    def __init__(self, request):
        """
        Initializes the cart.
        - The cart is always stored in the database.
        - For anonymous users, the cart is associated with their session key.
        - For authenticated users, the cart is associated with their user account.
        - It handles the merging of a session-based cart into a user's cart upon login.
        """
        self.session = request.session
        self.user = request.user
        cart = None

        if self.user.is_authenticated:
            cart, created = CartModel.objects.get_or_create(user=self.user)
            session_key = self.session.get(settings.CART_SESSION_ID)
            if session_key:
                try:
                    session_cart = CartModel.objects.get(session_key=session_key)
                    for item in session_cart.items.all():
                        cart_item, item_created = CartItem.objects.get_or_create(
                            cart=cart,
                            product=item.product,
                            defaults={'quantity': item.quantity}
                        )
                        if not item_created:
                            cart_item.quantity += item.quantity
                            cart_item.save()
                    session_cart.delete()
                    del self.session[settings.CART_SESSION_ID]
                    self.session.modified = True
                except CartModel.DoesNotExist:
                    pass
        else:
            session_key = self.session.get(settings.CART_SESSION_ID)
            if not session_key:
                self.session.cycle_key()
                session_key = self.session.session_key
                self.session[settings.CART_SESSION_ID] = session_key
            cart, created = CartModel.objects.get_or_create(session_key=session_key)

        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        """
        Adds a product to the cart or updates its quantity.
        """
        cart_item, created = CartItem.objects.get_or_create(
            cart=self.cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            if override_quantity:
                cart_item.quantity = quantity
            else:
                cart_item.quantity += quantity
            cart_item.save()

    def remove(self, product):
        """
        Removes a product from the cart.
        """
        CartItem.objects.filter(cart=self.cart, product=product).delete()

    def __iter__(self):
        """
        Iterates over the items in the cart, yielding product details.
        """
        for item in self.cart.items.prefetch_related('product'):
            yield {
                'product': item.product,
                'quantity': item.quantity,
                'price': item.product.price,
                'total_price': item.product.price * item.quantity,
            }

    def __len__(self):
        """
        Returns the total number of items in the cart.
        """
        return sum(item.quantity for item in self.cart.items.all())

    def get_total_price(self):
        """
        Calculates the total price of all items in the cart.
        """
        return sum(item.product.price * item.quantity for item in self.cart.items.all())

    def clear(self):
        """
        Removes all items from the cart.
        """
        self.cart.items.all().delete()
        if not self.user.is_authenticated:
            self.cart.coupon = None
            self.cart.save()

    @property
    def coupon(self):
        """
        Retrieves the currently applied coupon from the database cart.
        """
        return self.cart.coupon

    def get_discount(self):
        """
        Calculates the discount amount based on the currently applied coupon.
        """
        if self.coupon:
            return (self.coupon.discount / Decimal(100)) * self.get_total_price()
        return Decimal(0)

    def get_total_price_after_discount(self):
        """
        Calculates the total price of the cart after applying the discount.
        """
        return self.get_total_price() - self.get_discount()

    def save(self):
        """
        This method is kept for compatibility but is no longer needed
        as the cart is always saved to the database.
        """
        pass
