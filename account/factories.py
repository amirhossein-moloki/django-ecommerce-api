import factory
from django.contrib.auth import get_user_model
from .models import Address


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    phone_number = factory.Sequence(lambda n: f"+100000000{n:03d}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user_{n}")
    first_name = "Test"
    last_name = "User"
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "defaultpassword"
        self.set_password(password)


class AdminUserFactory(UserFactory):
    is_staff = True
    is_superuser = True


class AddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Address

    user = factory.SubFactory(UserFactory)
    province = "Test Province"
    city = "Test City"
    postal_code = factory.Faker("zipcode")
    full_address = "123 Test Street"
    receiver_name = "Test Receiver"
    receiver_phone = factory.Sequence(lambda n: f"+1999999{n:05d}")
