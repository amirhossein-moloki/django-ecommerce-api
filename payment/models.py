from django.db import models
from django.utils import timezone

from orders.models import Order


class PaymentTransaction(models.Model):
    class EventType(models.TextChoices):
        INITIATE = "initiate", "Initiate"
        VERIFY = "verify", "Verify"
        CALLBACK = "callback", "Callback"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"
        REJECTED = "rejected", "Rejected"

    order = models.ForeignKey(
        Order,
        related_name="payment_transactions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    track_id = models.CharField(max_length=100, db_index=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    amount = models.PositiveBigIntegerField(null=True, blank=True)
    result_code = models.CharField(max_length=20, blank=True)
    ref_id = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signature = models.CharField(max_length=128, blank=True)
    message = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "status"]),
            models.Index(fields=["order", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["track_id", "event_type", "status"],
                condition=models.Q(status="processed", event_type="verify"),
                name="unique_successful_verification",
            )
        ]

    def __str__(self):
        return f"PaymentTransaction({self.track_id}, {self.event_type}, {self.status})"
