from django_filters import FilterSet, RangeFilter, BooleanFilter
from rest_framework.filters import BaseFilterBackend

from .models import Product
from .utils import search_products


class ProductFilter(FilterSet):
    """
    FilterSet for Product model.
    This filter allows filtering products based on various fields such as
    name, description, category, and tags.
    """

    price = RangeFilter(method='filter_by_price_range')
    in_stock = BooleanFilter(method='filter_in_stock')

    class Meta:
        model = Product
        fields = {
            "name": ["exact", "icontains"],
            "description": ["icontains"],
            "category__slug": ["exact"],
            "category__name": ["exact", "icontains"],
            "tags__name": ["exact", "icontains"],
        }

    def filter_by_price_range(self, queryset, name, value):
        if value:
            return queryset.filter(
                variants__price__gte=value.start,
                variants__price__lte=value.stop
            ).distinct()
        return queryset

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(variants__stock__gt=0).distinct()
        return queryset


class ProductSearchFilterBackend(BaseFilterBackend):
    """
    Custom filter to search products by name and description.
    """

    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get("search", None)
        return search_products(queryset, search)
