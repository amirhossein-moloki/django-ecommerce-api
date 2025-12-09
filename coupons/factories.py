from datetime import timedelta
import factory
from django.utils import timezone
from .models import Coupon

class CouponFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Coupon

    code = factory.Sequence(lambda n: f'COUPON{n}')
    valid_from = factory.LazyFunction(timezone.now)
    valid_to = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    discount_percent = factory.Faker('random_int', min=5, max=50)
    max_usage_count = factory.Faker('random_int', min=10, max=100)
    is_active = True
