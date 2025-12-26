import factory
from factory.django import DjangoModelFactory

from account.tests.factories import UserFactory, AddressFactory
from orders.models import Order, OrderItem
from shop.tests.factories import ProductVariantFactory


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    address = factory.SubFactory(AddressFactory, user=factory.SelfAttribute("..user"))


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = factory.Faker("random_int", min=1, max=5)
    price = factory.SelfAttribute("variant.price")
