from .models import Order
from .serializers import OrderCreateSerializer
from .tasks import send_order_confirmation_email


def get_user_orders(user):
    if user.is_staff:
        return Order.objects.prefetch_related('items__product', 'user', 'address', 'coupon')
    return Order.objects.filter(user=user).prefetch_related('items__product', 'user', 'address', 'coupon')


def create_order(user, validated_data):
    serializer = OrderCreateSerializer(data=validated_data, context={'request': {'user': user}})
    serializer.is_valid(raise_exception=True)
    order = serializer.save()
    send_order_confirmation_email.delay(order.order_id)
    return order
