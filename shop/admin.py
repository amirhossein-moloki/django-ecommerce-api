from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (
    Category,
    Product,
    OptionType,
    OptionValue,
    ProductVariant,
    VariantOptionValue,
)

@admin.register(OptionType)
class OptionTypeAdmin(ModelAdmin):
    pass

@admin.register(OptionValue)
class OptionValueAdmin(ModelAdmin):
    pass

@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    pass

@admin.register(VariantOptionValue)
class VariantOptionValueAdmin(ModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("name", "category", "slug")
    list_filter = ("category", "tags")
    search_fields = ("name", "description", "category__name", "tags__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)
    inlines = [ProductVariantInline]
