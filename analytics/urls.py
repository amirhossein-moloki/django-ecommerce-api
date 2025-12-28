from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalyticsViewSet

router = DefaultRouter()
router.register(r'', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('overview/', AnalyticsViewSet.as_view({'get': 'overview'}), name='analytics-overview'),
    path('products/', AnalyticsViewSet.as_view({'get': 'products'}), name='analytics-products'),
    path('', include(router.urls)),
]
