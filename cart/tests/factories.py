import factory
from django.contrib.auth import get_user_model
from shop.models import Category, Product, ProductVariant
from cart.models import Cart, CartItem

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('phone_number',)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Sequence(lambda n: f'testuser{n}')
    phone_number = factory.Sequence(lambda n: f'+98912{n:07d}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpassword')


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    description = factory.Faker("paragraph")
    category = factory.SubFactory(CategoryFactory)
    user = factory.SubFactory(UserFactory)
    weight = 1.0
    length = 10.0
    width = 10.0
    height = 10.0


class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    price = factory.Faker("pydecimal", left_digits=5, right_digits=2, positive=True)
    stock = factory.Faker("random_int", min=1, max=100)
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")


class CartFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cart

    user = factory.SubFactory(UserFactory)


class CartItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = 1
