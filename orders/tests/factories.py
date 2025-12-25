import factory
from factory.django import DjangoModelFactory
from orders.models import Order, OrderItem
from account.tests.factories import UserFactory
from shop.tests.factories import ProductVariantFactory


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    status = factory.Faker("random_element", elements=[s[0] for s in Order.Status.choices])


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = factory.Faker("random_int", min=1, max=5)
    price = factory.LazyAttribute(lambda o: o.variant.price)
