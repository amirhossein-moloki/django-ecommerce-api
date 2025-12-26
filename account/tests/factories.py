import factory
from faker import Faker
from account.models import UserAccount, Address

fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserAccount
        django_get_or_create = ("phone_number",)

    @factory.post_generation
    def addresses(self, create, extracted, **kwargs):
        if not create:
            return
        AddressFactory.create_batch(1, user=self)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.LazyAttribute(
        lambda o: f"{o.first_name.lower()}{o.last_name.lower()}"
        f"{fake.random_int(1,100)}"
    )
    email = factory.Faker("email")
    phone_number = factory.Sequence(lambda n: f"+989000000{n:03d}")
    password = factory.PostGenerationMethodCall("set_password", "testpassword")
    is_active = True


class AddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Address

    user = factory.SubFactory(UserFactory)
    province = factory.Faker("state")
    city = factory.Faker("city")
    postal_code = factory.Faker("zipcode")
    full_address = factory.Faker("address")
    receiver_name = factory.LazyAttribute(
        lambda o: f"{o.user.first_name} {o.user.last_name}"
    )
    receiver_phone = factory.LazyAttribute(lambda o: o.user.phone_number)
