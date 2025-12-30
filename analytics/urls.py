from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalyticsViewSet

router = DefaultRouter()
router.register(r"", AnalyticsViewSet, basename="analytics")

urlpatterns = [
    path(
        "kpis/",
        AnalyticsViewSet.as_view({"get": "kpis"}),
        name="analytics-kpis",
    ),
    path(
        "sales-over-time/",
        AnalyticsViewSet.as_view({"get": "sales_over_time"}),
        name="analytics-sales-over-time",
    ),
    path(
        "order-status-breakdown/",
        AnalyticsViewSet.as_view({"get": "order_status_breakdown"}),
        name="analytics-order-status-breakdown",
    ),
    path(
        "products/",
        AnalyticsViewSet.as_view({"get": "products"}),
        name="analytics-products",
    ),
    path("", include(router.urls)),
]
