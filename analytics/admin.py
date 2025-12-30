from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from unfold.admin import ModelAdmin
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from .models import Refund, ProductDailyMetrics, AnalyticsDashboard


@admin.register(AnalyticsDashboard)
class AnalyticsDashboardAdmin(ModelAdmin):
    def get_urls(self):
        # Get the default URLs from the parent class
        urls = super().get_urls()

        # Define custom URLs
        custom_urls = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="analytics_dashboard",
            ),
        ]

        # The custom URL is placed at the beginning of the list to ensure
        # it is matched before any default URLs.
        return custom_urls + urls

    def dashboard_view(self, request):
        """
        Custom admin view to render the analytics dashboard.
        """
        # Prepare context data for the template
        context = {
            **self.admin_site.each_context(request),
            "title": "Analytics Dashboard",
            "subtitle": "A comprehensive overview of your store's performance.",
            # Additional context variables can be added here if needed
        }

        # Render the custom dashboard template
        return render(request, "admin/analytics_dashboard.html", context)


@admin.register(Refund)
class RefundAdmin(ModelAdmin):
    list_display = ("order_item", "refund_date", "refund_amount")
    search_fields = ("order_item__order__order_id",)


@admin.register(ProductDailyMetrics)
class ProductDailyMetricsAdmin(ModelAdmin):
    list_display = ("product", "date", "units_sold", "revenue", "profit")
    list_filter = ("date", "product")
    search_fields = ("product__name",)

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context,
        )
        try:
            qs = response.context_data["cl"].queryset
        except (AttributeError, KeyError):
            return response

        metrics = {
            "total_sales": Sum("revenue"),
            "total_products_sold": Sum("units_sold"),
        }
        chart_data = self.get_chart_data(qs)
        response.context_data["chart_data"] = chart_data
        return response

    def get_chart_data(self, qs):
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
                "labels": [s["month"].strftime("%Y-%m") for s in sales_per_month],
                "data": [float(s["total_revenue"]) for s in sales_per_month],
            },
            "top_products": {
                "labels": [p["product__name"] for p in top_products],
                "data": [p["total_sold"] for p in top_products],
            },
        }
        return chart_data
