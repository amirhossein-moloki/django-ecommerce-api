from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import ProductDailyMetrics
from .serializers import ProductDailyMetricsSerializer, ProductPerformanceSerializer
from django.db.models import Sum, F
from shop.models import Product


class AnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductDailyMetrics.objects.all()
    serializer_class = ProductDailyMetricsSerializer

    @action(detail=False, methods=['get'])
    def overview(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = self.get_queryset()
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        aggregates = queryset.aggregate(
            total_revenue=Sum('revenue'),
            total_profit=Sum('profit'),
            total_units_sold=Sum('units_sold'),
        )

        return Response(aggregates)

    @action(detail=False, methods=['get'])
    def products(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = ProductDailyMetrics.objects.all()
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        product_performance = queryset.values(
            'product__product_id', 'product__name'
        ).annotate(
            total_units_sold=Sum('units_sold'),
            total_revenue=Sum('revenue'),
            total_profit=Sum('profit'),
        ).order_by('-total_revenue')

        # This is a workaround to rename the annotated fields to match the serializer
        # A better solution would be to use a custom serializer or a different approach
        # to building the response.
        data = [
            {
                'product_id': item['product__product_id'],
                'product_name': item['product__name'],
                'total_units_sold': item['total_units_sold'],
                'total_revenue': item['total_revenue'],
                'total_profit': item['total_profit'],
            }
            for item in product_performance
        ]

        serializer = ProductPerformanceSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
