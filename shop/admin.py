from django.contrib import admin

from .models import Category, Product, OptionType, OptionValue, ProductVariant, VariantOptionValue

admin.site.register(OptionType)
admin.site.register(OptionValue)
admin.site.register(ProductVariant)
admin.site.register(VariantOptionValue)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug")
    list_filter = ("category", "tags")
    search_fields = ("name", "description", "category__name", "tags__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)
    inlines = [ProductVariantInline]
