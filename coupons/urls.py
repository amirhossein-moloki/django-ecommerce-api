from django.urls import path
from .views import CouponViewSet

urlpatterns = [
    path('coupons/apply/', CouponViewSet.as_view({'post': 'apply'}), name='coupon-apply'),
]
