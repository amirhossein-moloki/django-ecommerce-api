from django.db import models
from shop.models import Product
from orders.models import OrderItem


class Refund(models.Model):
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE)
    reason = models.TextField()
    refund_date = models.DateTimeField(auto_now_add=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Refund for {self.order_item}"


class ProductDailyMetrics(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date = models.DateField()
    units_sold = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ("product", "date")
        verbose_name_plural = "Product Daily Metrics"

    def __str__(self):
        return f"{self.product.name} - {self.date}"


class AnalyticsDashboard(ProductDailyMetrics):
    class Meta:
        proxy = True
        verbose_name = "Analytics Dashboard"
        verbose_name_plural = "Analytics Dashboard"
