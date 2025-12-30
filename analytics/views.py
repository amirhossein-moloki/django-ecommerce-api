from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import ProductDailyMetrics
from .serializers import ProductDailyMetricsSerializer, ProductPerformanceSerializer
from django.db.models import Sum, Count
from orders.models import Order
from account.models import UserAccount


class AnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductDailyMetrics.objects.all()
    serializer_class = ProductDailyMetricsSerializer

    @action(detail=False, methods=["get"])
    def kpis(self, request):
        """
        Returns key performance indicators.
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)

        total_revenue = (
            ProductDailyMetrics.objects.aggregate(total_revenue=Sum("revenue"))[
                "total_revenue"
            ]
            or 0
        )
        total_orders = Order.objects.filter(status=Order.Status.PAID).count()
        total_customers = UserAccount.objects.count()
        new_customers = UserAccount.objects.filter(
            date_joined__gte=thirty_days_ago
        ).count()

        return Response(
            {
                "data": {
                    "total_revenue": total_revenue,
                    "total_orders": total_orders,
                    "total_customers": total_customers,
                    "new_customers": new_customers,
                }
            }
        )

    @action(detail=False, methods=["get"])
    def sales_over_time(self, request):
        """
        Returns sales data aggregated by date.
        """
        sales_data = (
            ProductDailyMetrics.objects.values("date")
            .annotate(daily_revenue=Sum("revenue"))
            .order_by("date")
        )
        return Response({"data": sales_data})

    @action(detail=False, methods=["get"])
    def order_status_breakdown(self, request):
        """
        Returns the count of orders for each status.
        """
        status_data = (
            Order.objects.values("status")
            .annotate(count=Count("status"))
            .order_by("status")
        )
        return Response({"data": status_data})

    @action(detail=False, methods=["get"])
    def products(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        queryset = ProductDailyMetrics.objects.all()
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        product_performance = (
            queryset.values("product__product_id", "product__name")
            .annotate(
                total_units_sold=Sum("units_sold"),
                total_revenue=Sum("revenue"),
                total_profit=Sum("profit"),
            )
            .order_by("-total_revenue")
        )

        # This is a workaround to rename the annotated fields to match the serializer
        # A better solution would be to use a custom serializer or a different approach
        # to building the response.
        data = [
            {
                "product_id": item["product__product_id"],
                "product_name": item["product__name"],
                "total_units_sold": item["total_units_sold"],
                "total_revenue": item["total_revenue"],
                "total_profit": item["total_profit"],
            }
            for item in product_performance
        ]

        serializer = ProductPerformanceSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response({"data": serializer.data})
