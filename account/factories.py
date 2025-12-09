import factory
from django.contrib.auth import get_user_model
from faker import Faker
from .models import Address

fake = Faker()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ('phone_number',)

    phone_number = factory.LazyAttribute(lambda _: fake.phone_number()[:13])
    email = factory.LazyAttribute(lambda o: f'{o.phone_number}@example.com')
    username = factory.LazyAttribute(lambda o: f'user_{o.phone_number}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted or 'defaultpassword')


class AdminUserFactory(UserFactory):
    is_staff = True
    is_superuser = True


class AddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Address

    user = factory.SubFactory(UserFactory)
    province = factory.Faker('city')
    city = factory.Faker('city')
    postal_code = factory.Faker('postcode')
    address_detail = factory.Faker('address')
    receiver_name = factory.Faker('name')
    receiver_phone_number = factory.LazyAttribute(lambda _: fake.phone_number()[:13])
