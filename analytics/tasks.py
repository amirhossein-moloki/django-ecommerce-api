from celery import shared_task
from django.utils import timezone
from shop.models import Product
from orders.models import OrderItem
from .models import ProductDailyMetrics
from django.db.models import Sum, F


@shared_task
def populate_daily_metrics():
    today = timezone.now().date()
    yesterday = today - timezone.timedelta(days=1)

    order_items = OrderItem.objects.filter(order__order_date__date=yesterday)

    for product in Product.objects.all():
        product_order_items = order_items.filter(variant__product=product)
        units_sold = product_order_items.aggregate(total_units=Sum('quantity'))['total_units'] or 0
        revenue = product_order_items.aggregate(total_revenue=Sum(F('quantity') * F('price')))['total_revenue'] or 0

        # This is a simplified profit calculation. A more accurate calculation
        # would require the cost of the product at the time of sale.
        cost = product_order_items.aggregate(total_cost=Sum(F('quantity') * F('variant__cost')))['total_cost'] or 0
        profit = revenue - cost if revenue and cost else 0

        ProductDailyMetrics.objects.update_or_create(
            product=product,
            date=yesterday,
            defaults={
                'units_sold': units_sold,
                'revenue': revenue,
                'profit': profit,
            }
        )
