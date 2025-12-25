from django.contrib import admin
from .models import Discount, DiscountRule, UserDiscountUsage

class DiscountRuleInline(admin.TabularInline):
    """
    Allows editing DiscountRule models on the Discount admin page.
    This provides a more intuitive interface for managing discount conditions.
    """
    model = DiscountRule
    extra = 1  # Show one empty form for a new rule by default
    filter_horizontal = ('products', 'categories', 'tags', 'variants')


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Discount model.
    """
    list_display = ('name', 'type', 'amount', 'valid_from', 'valid_to', 'active', 'usage_count', 'max_usage')
    list_filter = ('type', 'active', 'valid_from', 'valid_to')
    search_fields = ('name',)
    inlines = [DiscountRuleInline]


@admin.register(UserDiscountUsage)
class UserDiscountUsageAdmin(admin.ModelAdmin):
    """
    Admin configuration for the UserDiscountUsage model.
    Provides a read-only view of user-specific discount usage.
    """
    list_display = ('user', 'discount', 'usage_count')
    search_fields = ('user__username', 'discount__name')
    readonly_fields = ('user', 'discount', 'usage_count')

    def has_add_permission(self, request):
        # Disable manual addition of usage records from the admin
        return False

    def has_change_permission(self, request, obj=None):
        # Disable manual editing of usage records from the admin
        return False
