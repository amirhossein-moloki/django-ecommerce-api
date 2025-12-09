import factory
from faker import Faker
from .models import Category, Product, Review
from account.factories import UserFactory
from decimal import Decimal

fake = Faker()

class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.LazyAttribute(lambda o: fake.slug(o.name))


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    name = factory.Sequence(lambda n: f'Product {n}')
    slug = factory.LazyAttribute(lambda o: fake.slug(o.name))
    description = factory.Faker('paragraph')
    price = factory.LazyAttribute(lambda _: Decimal(fake.random_int(min=10000, max=1000000)))
    stock = factory.Faker('random_int', min=0, max=100)
    weight = factory.LazyAttribute(lambda _: Decimal(fake.random_int(min=100, max=5000)))
    length = factory.LazyAttribute(lambda _: Decimal(fake.random_int(min=10, max=100)))
    width = factory.LazyAttribute(lambda _: Decimal(fake.random_int(min=10, max=100)))
    height = factory.LazyAttribute(lambda _: Decimal(fake.random_int(min=10, max=100)))


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    product = factory.SubFactory(ProductFactory)
    user = factory.SubFactory(UserFactory)
    rating = factory.Faker('random_int', min=1, max=5)
    comment = factory.Faker('sentence')
