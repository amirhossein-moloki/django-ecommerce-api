import factory
from decimal import Decimal
from account.factories import UserFactory
from .models import Category, Product, Review, ProductVariant


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.LazyAttribute(
        lambda o: f"category-{o.name.lower().replace(' ', '-')}"
    )


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    description = "Sample product description"
    category = factory.SubFactory(CategoryFactory)
    user = factory.SubFactory(UserFactory)
    weight = Decimal("1.00")
    length = Decimal("10.00")
    width = Decimal("10.00")
    height = Decimal("10.00")
    is_fragile = False
    is_liquid = False

    @factory.post_generation
    def variants(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for variant_data in extracted:
                ProductVariantFactory(product=self, **variant_data)
        else:
            # Default variant
            ProductVariantFactory(product=self, **kwargs)


class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    price = Decimal("100.00")
    stock = 10
    sku = factory.Sequence(lambda n: f"SKU-{n}")


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    product = factory.SubFactory(ProductFactory)
    user = factory.SubFactory(UserFactory)
    rating = 3
    comment = "Test review comment"
