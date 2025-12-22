from django.urls import path
from .views import ProductChatAPIView

urlpatterns = [
    path('chat/<uuid:product_id>/', ProductChatAPIView.as_view(), name='product-chat'),
]
