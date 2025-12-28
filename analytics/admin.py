from django.contrib import admin
from .models import Refund, ProductDailyMetrics


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('order_item', 'refund_date', 'refund_amount')
    search_fields = ('order_item__order__order_id',)


@admin.register(ProductDailyMetrics)
class ProductDailyMetricsAdmin(admin.ModelAdmin):
    list_display = ('product', 'date', 'units_sold', 'revenue', 'profit')
    list_filter = ('date', 'product')
    search_fields = ('product__name',)
