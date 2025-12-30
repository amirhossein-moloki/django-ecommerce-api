from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from taggit.models import Tag

from shop.models import Product, Category, ProductVariant


class Discount(models.Model):
    DISCOUNT_TYPE_PERCENTAGE = "percentage"
    DISCOUNT_TYPE_FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_TYPE_PERCENTAGE, "Percentage"),
        (DISCOUNT_TYPE_FIXED, "Fixed Amount"),
    ]

    name = models.CharField(max_length=255, verbose_name="Discount Name")
    code = models.CharField(
        max_length=50, unique=True, null=True, blank=True, verbose_name="Discount Code"
    )
    type = models.CharField(
        max_length=10, choices=DISCOUNT_TYPE_CHOICES, verbose_name="Discount Type"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Discount Amount",
    )
    valid_from = models.DateTimeField(verbose_name="Valid From")
    valid_to = models.DateTimeField(verbose_name="Valid To")
    active = models.BooleanField(default=True, verbose_name="Is Active")
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)],
        verbose_name="Minimum Purchase Amount",
    )
    max_usage = models.PositiveIntegerField(
        default=1, verbose_name="Maximum Overall Usage"
    )
    usage_count = models.PositiveIntegerField(
        default=0, editable=False, verbose_name="Usage Count"
    )
    usage_per_user = models.PositiveIntegerField(
        default=1, verbose_name="Maximum Usage Per User"
    )

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        ordering = ["-valid_from"]

    def __str__(self):
        return self.name

    def is_valid(self):
        """Checks if the discount is currently active and within its validity period."""
        return self.active and self.valid_from <= timezone.now() <= self.valid_to


class DiscountRule(models.Model):
    discount = models.ForeignKey(
        Discount,
        related_name="rules",
        on_delete=models.CASCADE,
        verbose_name="Discount",
    )
    products = models.ManyToManyField(
        Product, blank=True, verbose_name="Applicable Products"
    )
    categories = models.ManyToManyField(
        Category, blank=True, verbose_name="Applicable Categories"
    )
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Applicable Tags")
    variants = models.ManyToManyField(
        ProductVariant, blank=True, verbose_name="Applicable Variants"
    )

    class Meta:
        verbose_name = "Discount Rule"
        verbose_name_plural = "Discount Rules"

    def __str__(self):
        return f"Rule for {self.discount.name}"


class UserDiscountUsage(models.Model):
    """Tracks the usage of a discount by a specific user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discount_usages",
    )
    discount = models.ForeignKey(
        Discount, on_delete=models.CASCADE, related_name="user_usages"
    )
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "discount")
        verbose_name = "User Discount Usage"
        verbose_name_plural = "User Discount Usages"

    def __str__(self):
        return f"Usage of {self.discount.name} by {self.user.get_username()}"
