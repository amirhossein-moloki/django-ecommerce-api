from rest_framework import serializers
from .models import ProductDailyMetrics


class ProductDailyMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDailyMetrics
        fields = ("date", "units_sold", "revenue", "profit")


class ProductPerformanceSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    total_units_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
