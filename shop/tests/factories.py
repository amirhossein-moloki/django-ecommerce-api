import factory
from factory.django import DjangoModelFactory
from shop.models import Category, Product, Review, ProductVariant
from account.tests.factories import UserFactory


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Faker("word")


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("paragraph")
    category = factory.SubFactory(CategoryFactory)
    user = factory.SubFactory(UserFactory)
    weight = 1.0
    length = 1.0
    width = 1.0
    height = 1.0

    @factory.post_generation
    def variants(self, create, extracted, **kwargs):
        if not create:
            return
        if not self.variants.exists():
            ProductVariantFactory(product=self)


class ProductVariantFactory(DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    stock = factory.Faker("random_int", min=0, max=100)
    sku = factory.Faker("ean")


class ReviewFactory(DjangoModelFactory):
    class Meta:
        model = Review

    product = factory.SubFactory(ProductFactory)
    user = factory.SubFactory(UserFactory)
    rating = factory.Faker("random_int", min=1, max=5)
    comment = factory.Faker("text")
