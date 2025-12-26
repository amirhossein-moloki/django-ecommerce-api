from decimal import Decimal

from django.conf import settings

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
        self.cart = None

        if self.user.is_authenticated:
            self.cart, created = CartModel.objects.get_or_create(user=self.user)
            session_key = self.session.get(settings.CART_SESSION_ID)
            if session_key:
                try:
                    session_cart = CartModel.objects.get(session_key=session_key)
                    for item in session_cart.items.all():
                        cart_item, item_created = CartItem.objects.get_or_create(
                            cart=self.cart,
                            variant=item.variant,
                            defaults={"quantity": item.quantity},
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
                self.session.modified = True
            self.cart, created = CartModel.objects.get_or_create(session_key=session_key)

    def add(self, variant, quantity=1, override_quantity=False):
        """
        Adds a product variant to the cart or updates its quantity.
        """
        cart_item, created = CartItem.objects.get_or_create(
            cart=self.cart, variant=variant, defaults={"quantity": quantity}
        )

        if not created:
            if override_quantity:
                cart_item.quantity = quantity
            else:
                cart_item.quantity += quantity
            cart_item.save()

    def remove(self, variant):
        """
        Removes a product variant from the cart.
        """
        CartItem.objects.filter(cart=self.cart, variant=variant).delete()

    def __iter__(self):
        """
        Iterates over the items in the cart, yielding variant details.
        """
        if not self.cart or not self.cart.pk:
            return
        for item in self.cart.items.prefetch_related("variant__product"):
            yield {
                "variant": item.variant,
                "quantity": item.quantity,
                "price": item.variant.price,
                "total_price": item.variant.price * item.quantity,
            }

    def __len__(self):
        """
        Returns the total number of items in the cart.
        """
        if not self.cart or not self.cart.pk:
            return 0
        return sum(item.quantity for item in self.cart.items.all())

    def get_total_price(self):
        """
        Calculates the total price of all items in the cart.
        """
        if not self.cart or not self.cart.pk:
            return Decimal("0")
        return sum(item.variant.price * item.quantity for item in self.cart.items.all())

    def clear(self):
        """
        Removes all items from the cart.
        """
        if self.cart and self.cart.pk:
            self.cart.delete()
        self.cart = None
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
            self.session.modified = True

    def get_discount(self):
        """
        Calculates the best automatic discount for the cart using the DiscountService.
        """
        from discounts.services import DiscountService

        # For the cart display, we only consider automatic discounts. Coded discounts are applied at checkout.
        discount_amount, _ = DiscountService.apply_discount(self, self.user)
        return discount_amount

    def get_total_price_after_discount(self):
        """
        Calculates the total price of the cart after applying the best discount.
        This method now ignores the old coupon system.
        """
        return self.get_total_price() - self.get_discount()

    def save(self):
        """
        This method is kept for compatibility but is no longer needed
        as the cart is always saved to the database.
        """
        pass
