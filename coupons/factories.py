import factory
from datetime import timedelta
from django.utils import timezone
from .models import Coupon


class CouponFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Coupon

    code = factory.Sequence(lambda n: f'COUPON{n}')
    valid_from = factory.LazyFunction(timezone.now)
    valid_to = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    discount = 10
    max_usage_count = 100
    is_active = True
