import factory
from .models import Order, OrderItem
from account.factories import UserFactory, AddressFactory
from coupons.factories import CouponFactory
from shop.factories import ProductFactory
from decimal import Decimal

class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    address = factory.SubFactory(AddressFactory)
    status = factory.Iterator([s[0] for s in Order.Status.choices])
    coupon = factory.SubFactory(CouponFactory)
    discount_amount = factory.LazyAttribute(
        lambda o: o.coupon.discount_percent if o.coupon else 0
    )


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = factory.Faker('random_int', min=1, max=5)
    price = factory.LazyAttribute(lambda o: o.product.price)
