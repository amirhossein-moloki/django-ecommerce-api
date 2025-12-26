import factory
from decimal import Decimal
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from shop.models import Product, ProductVariant
from payment.models import PaymentTransaction

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "testpassword")


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Faker("sentence", nb_words=3)
    slug = factory.Faker("slug")


class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    price = factory.Faker("pydecimal", left_digits=5, right_digits=2, positive=True)
    stock = 10
    sku = factory.Faker("ean")


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    total_payable = Decimal("0.00")  # Will be recalculated in tests


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    price = factory.SelfAttribute("variant.price")
    quantity = 2
    product_name = factory.SelfAttribute("variant.product.name")


class PaymentTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentTransaction

    order = factory.SubFactory(OrderFactory)
    track_id = factory.Faker("pystr", max_chars=20)
    event_type = PaymentTransaction.EventType.INITIATE
    status = PaymentTransaction.Status.RECEIVED
    amount = factory.Faker("pyint", min_value=10000, max_value=1000000)
