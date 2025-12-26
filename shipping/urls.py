from django.urls import path
from .views import CityListAPIView, CalculateShippingCostAPIView

app_name = "shipping"

urlpatterns = [
    path("cities/", CityListAPIView.as_view(), name="city-list"),
    path(
        "calculate-cost/", CalculateShippingCostAPIView.as_view(), name="calculate-cost"
    ),
]
