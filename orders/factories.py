import factory
from decimal import Decimal
from account.factories import AddressFactory, UserFactory
from coupons.factories import CouponFactory
from shop.factories import ProductFactory, ProductVariantFactory
from .models import Order, OrderItem


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    address = factory.SubFactory(AddressFactory)
    status = Order.Status.PENDING
    shipping_cost = Decimal("0.00")
    tax_amount = Decimal("0.00")


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = 1
    price = factory.LazyAttribute(lambda o: o.variant.price)
    product_name = factory.LazyAttribute(lambda o: o.variant.product.name)
    product_sku = factory.LazyAttribute(lambda o: o.variant.sku)
