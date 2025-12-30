from django import template
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
import json

from analytics.models import ProductDailyMetrics
from orders.models import Order
from account.models import UserAccount

register = template.Library()


@register.inclusion_tag("analytics/templatetags/dashboard_summary.html")
def dashboard_summary():
    """
    Provides the data for the admin dashboard summary.
    """
    # --- KPIs ---
    thirty_days_ago = timezone.now() - timedelta(days=30)
    total_revenue = (
        ProductDailyMetrics.objects.aggregate(total_revenue=Sum("revenue"))[
            "total_revenue"
        ]
        or 0
    )
    total_orders = Order.objects.filter(status=Order.Status.PAID).count()
    total_customers = UserAccount.objects.count()
    new_customers = UserAccount.objects.filter(date_joined__gte=thirty_days_ago).count()

    kpis = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "new_customers": new_customers,
    }

    # --- Chart Data ---
    qs = ProductDailyMetrics.objects.all()

    # Sales per month
    sales_per_month = (
        qs.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total_revenue=Sum("revenue"))
        .order_by("month")
    )

    # Top 5 selling products
    top_products = (
        qs.values("product__name")
        .annotate(total_sold=Sum("units_sold"))
        .order_by("-total_sold")[:5]
    )

    chart_data = {
        "sales_per_month": {
            "labels": json.dumps(
                [s["month"].strftime("%Y-%m") for s in sales_per_month]
            ),
            "data": json.dumps([float(s["total_revenue"]) for s in sales_per_month]),
        },
        "top_products": {
            "labels": json.dumps([p["product__name"] for p in top_products]),
            "data": json.dumps([p["total_sold"] for p in top_products]),
        },
    }

    return {
        "kpis": kpis,
        "chart_data": chart_data,
    }
