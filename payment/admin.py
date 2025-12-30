from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    list_display = (
        "track_id",
        "event_type",
        "status",
        "order",
        "amount",
        "result_code",
        "created_at",
    )
    list_filter = ("event_type", "status")
    search_fields = ("track_id", "order__order_id", "ref_id")
    readonly_fields = ("created_at", "updated_at", "raw_payload", "gateway_response")
