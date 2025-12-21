from django.urls import path
from .views import CityListView, CalculateShippingCostAPIView

app_name = 'shipping'

urlpatterns = [
    path('cities/', CityListView.as_view(), name='city-list'),
    path('calculate-cost/', CalculateShippingCostAPIView.as_view(), name='calculate-cost'),
]
