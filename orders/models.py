import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django_prometheus.models import ExportModelOperationsMixin
from simple_history.models import HistoricalRecords

from coupons.models import Coupon
from shop.models import Product
from account.models import Address
from django.core.exceptions import ValidationError

User = get_user_model()


class Order(ExportModelOperationsMixin('order'), models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        PROCESSING = 'processing', 'Processing'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELED = 'canceled', 'Canceled'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name='orders', on_delete=models.SET_NULL, null=True)
    address = models.ForeignKey(Address, related_name='orders', on_delete=models.SET_NULL, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    coupon = models.ForeignKey(Coupon, related_name='orders', on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.CharField(max_length=3, default='IRT')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    payment_gateway = models.CharField(max_length=50, blank=True)
    payment_ref_id = models.CharField(max_length=100, blank=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True)
    payment_track_id = models.CharField(max_length=100, blank=True)
    postex_shipment_id = models.CharField(max_length=100, blank=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    shipping_label_url = models.URLField(blank=True)
    shipping_provider = models.CharField(max_length=50, blank=True)
    shipping_status = models.CharField(max_length=50, blank=True)
    shipping_tracking_code = models.CharField(max_length=100, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_payable = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    history = HistoricalRecords()

    # Define valid state transitions
    _transitions = {
        Status.PENDING: [Status.PAID, Status.CANCELED],
        Status.PAID: [Status.PROCESSING, Status.CANCELED],
        Status.PROCESSING: [Status.SHIPPED, Status.CANCELED],
        Status.SHIPPED: [Status.DELIVERED],
        Status.DELIVERED: [],
        Status.CANCELED: [],
    }

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['-order_date']),
        ]
        ordering = ["-order_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status

    def clean(self):
        """
        Validate state transitions before saving.
        """
        if self.pk and self._original_status != self.status:
            if self.status not in self._transitions.get(self._original_status, []):
                raise ValidationError(f"Invalid state transition from '{self._original_status}' to '{self.status}'.")

    def save(self, *args, **kwargs):
        """
        Override save to validate state transitions and restore stock on cancellation.
        """
        self.clean()  # Perform validation

        # Check if the order is being canceled
        if self.status == self.Status.CANCELED and self._original_status != self.Status.CANCELED:
            self.restore_stock()

        super().save(*args, **kwargs)
        self._original_status = self.status  # Update original status after save

    def restore_stock(self):
        """
        Restore the stock for all items in a canceled order.
        """
        for item in self.items.all():
            product = item.product
            product.stock += item.quantity
            product.save(update_fields=['stock'])

    def get_total_cost_before_discount(self):
        """
        Calculate the total cost of all items in the order before applying any discounts.

        Returns:
            Decimal: The total cost of all order items.
        """
        return sum(item.get_cost() for item in self.items.all())

    def get_discount(self):
        """
        Calculate the discount amount for the order based on the associated coupon.

        Returns:
            Decimal: The discount amount. Returns 0 if no coupon is applied.
        """
        total_cost = self.get_total_cost_before_discount()
        if self.coupon:
            return total_cost * (self.coupon.discount / Decimal(100))
        return Decimal(0)

    @property
    def total_price(self):
        """
        Calculate the total price of the order after applying any discounts.

        Returns:
            Decimal: The total price, which is the total cost of all order items minus the discount.
        """
        total_cost = self.get_total_cost_before_discount()
        return total_cost - self.get_discount()

    def calculate_total_payable(self):
        """
        Calculates the final amount to be paid by the user.
        """
        self.subtotal = self.get_total_cost_before_discount()
        self.discount_amount = self.get_discount()
        total = self.subtotal - self.discount_amount + self.shipping_cost + self.tax_amount
        self.total_payable = total
        return self.total_payable

    def __str__(self):
        return f"Order: {self.order_id} by {self.user.username if self.user else 'Deleted User'}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]
        ordering = ["order"]

    def get_cost(self):
        return self.price * self.quantity

    def __str__(self):
        return f"Order Item: {self.product.name} (Order ID: {self.order.order_id})"
