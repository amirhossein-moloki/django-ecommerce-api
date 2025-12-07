from django.urls import path

from payment.views import PaymentProcessAPIView, PaymentVerifyAPIView, PaymentWebhookAPIView

app_name = 'payment'

urlpatterns = [
    path('process/<uuid:order_id>/', PaymentProcessAPIView.as_view(), name='process'),
    path('verify/', PaymentVerifyAPIView.as_view(), name='verify'),
    path('webhook/', PaymentWebhookAPIView.as_view(), name='webhook'),
]
