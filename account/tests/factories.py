import factory
from faker import Faker
from account.models import UserAccount

fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserAccount
        django_get_or_create = ('phone_number',)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.LazyAttribute(lambda o: f'{o.first_name.lower()}{o.last_name.lower()}' f'{fake.random_int(1,100)}')
    email = factory.Faker("email")
    phone_number = factory.LazyAttribute(lambda _: fake.numerify(text='+989#########'))
    password = factory.PostGenerationMethodCall('set_password', 'testpassword')
    is_active = True
