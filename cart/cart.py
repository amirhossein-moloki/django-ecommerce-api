from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404

from coupons.models import Coupon
from shop.models import Product
from .models import Cart as CartModel, CartItem


class Cart:
    """
    A unified cart class that handles both session-based (for anonymous users)
    and database-based (for authenticated users) carts.
    """

    def __init__(self, request):
        """
        Initializes the cart.
        - If the user is authenticated, it retrieves or creates a database cart.
        - If the user is anonymous, it uses a session-based cart.
        - It also handles the merging of a session cart into the database upon user login.
        """
        self.session = request.session
        self.user = request.user
        self.cart = None
        self.coupon_id = None

        if self.user.is_authenticated:
            # For authenticated users, use the database cart.
            self.cart, created = CartModel.objects.get_or_create(user=self.user)
            self.coupon_id = self.cart.coupon.id if self.cart.coupon else None
        else:
            # For anonymous users, use the session cart.
            cart_session = self.session.get(settings.CART_SESSION_ID)
            if not cart_session:
                cart_session = self.session[settings.CART_SESSION_ID] = {}
            self.cart = cart_session
            self.coupon_id = self.session.get('coupon_id')

    def merge_session_cart(self):
        """
        Merges the session cart into the database cart when a user logs in.
        - Items from the session cart are added to the user's database cart.
        - The session cart is then cleared.
        """
        if self.user.is_authenticated:
            session_cart = self.session.get(settings.CART_SESSION_ID)
            if session_cart:
                for product_id, item_data in session_cart.items():
                    product = get_object_or_404(Product, product_id=product_id)
                    cart_item, created = CartItem.objects.get_or_create(cart=self.cart, product=product)
                    if not created:
                        cart_item.quantity += item_data['quantity']
                    else:
                        cart_item.quantity = item_data['quantity']
                    cart_item.save()
                # Clear the session cart after merging.
                del self.session[settings.CART_SESSION_ID]
                self.session.modified = True

    def add(self, product, quantity=1, override_quantity=False):
        """
        Adds a product to the cart or updates its quantity.
        """
        if self.user.is_authenticated:
            cart_item, created = CartItem.objects.get_or_create(cart=self.cart, product=product)
            if not created:
                if override_quantity:
                    cart_item.quantity = quantity
                else:
                    cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()
        else:
            product_id = str(product.product_id)
            if product_id not in self.cart:
                self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}
            if override_quantity:
                self.cart[product_id]['quantity'] = quantity
            else:
                self.cart[product_id]['quantity'] += quantity
            self.save()

    def remove(self, product):
        """
        Removes a product from the cart.
        """
        if self.user.is_authenticated:
            CartItem.objects.filter(cart=self.cart, product=product).delete()
        else:
            product_id = str(product.product_id)
            if product_id in self.cart:
                del self.cart[product_id]
                self.save()

    def __iter__(self):
        """
        Iterates over the items in the cart.
        """
        if self.user.is_authenticated:
            cart_items = self.cart.items.all()
            for item in cart_items:
                yield {
                    'product': item.product,
                    'quantity': item.quantity,
                    'price': item.product.price,
                    'total_price': item.product.price * item.quantity,
                }
        else:
            product_ids = self.cart.keys()
            products = Product.objects.filter(product_id__in=product_ids)
            cart = self.cart.copy()
            for product in products:
                cart[str(product.product_id)]['product'] = product
            for item in cart.values():
                item['price'] = Decimal(item['price'])
                item['total_price'] = item['price'] * item['quantity']
                yield item

    def __len__(self):
        """
        Returns the total number of items in the cart.
        """
        if self.user.is_authenticated:
            return sum(item.quantity for item in self.cart.items.all())
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        Calculates the total price of all items in the cart.
        """
        if self.user.is_authenticated:
            return sum(item.product.price * item.quantity for item in self.cart.items.all())
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def save(self):
        """
        Saves the cart to the session (for anonymous users).
        """
        if not self.user.is_authenticated:
            self.session.modified = True

    def clear(self):
        """
        Clears the cart.
        """
        if self.user.is_authenticated:
            self.cart.items.all().delete()
        else:
            self.cart.clear()
            if 'coupon_id' in self.session:
                del self.session['coupon_id']
            self.save()

    @property
    def coupon(self):
        """
        Retrieves the currently applied coupon.
        """
        if self.coupon_id:
            try:
                return Coupon.objects.get(id=self.coupon_id)
            except Coupon.DoesNotExist:
                pass
        return None

    def get_discount(self, coupon=None):
        """
        Calculates the discount amount based on the provided coupon.
        """
        applied_coupon = coupon if coupon is not None else self.coupon
        if applied_coupon:
            return (applied_coupon.discount / Decimal(100)) * self.get_total_price()
        return Decimal(0)

    def get_total_price_after_discount(self):
        """
        Calculates the total price of the cart after applying the discount.
        """
        return self.get_total_price() - self.get_discount()
