from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ("code", "valid_from", "valid_to", "discount", "active")
    list_filter = ("active", "valid_from", "valid_to")
    search_fields = ("code",)
