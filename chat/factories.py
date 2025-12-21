from chat.models import Message
from shop.factories import ProductFactory, UserFactory
import factory


class MessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message

    sender = factory.SubFactory(UserFactory)
    recipient = factory.SubFactory(UserFactory)
    product = factory.SubFactory(ProductFactory)
    content = factory.Faker('sentence')
