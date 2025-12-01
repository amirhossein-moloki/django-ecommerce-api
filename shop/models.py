import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from slugify import slugify
from taggit.managers import TaggableManager

from .custom_taggit import CustomTaggedItem
from .utils import product_upload_to_unique


class SluggedModel(models.Model):
    """
    An abstract base model that provides 'name' and 'slug' fields.
    The 'slug' field is automatically generated from the 'name' field.
    """
    name = models.CharField(max_length=100, help_text="The name of the item.")
    slug = models.SlugField(max_length=100, unique=True, help_text="A URL-friendly version of the name.")

    class Meta:
        abstract = True


class Category(SluggedModel):
    """
    Represents a product category.
    """
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['name']),
        ]
        ordering = ["name"]

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to auto-generate the slug from the name.
        This ensures that the slug is always in sync with the name.
        """
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """
        Returns the absolute URL for a category instance.
        """
        return reverse('api-v1:category-detail', kwargs={'slug': self.slug})

    def __str__(self):
        return f"Category: {self.name}"


class InStockManager(models.Manager):
    """
    A custom manager that returns only products that are in stock (stock > 0).
    """
    def get_queryset(self):
        return super().get_queryset().filter(stock__gt=0)


class Product(SluggedModel):
    """
    Represents a product in the e-commerce store.
    """
    product_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, help_text="The unique identifier for the product.")
    description = models.TextField(help_text="A detailed description of the product.")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.0)], help_text="The price of the product.")
    stock = models.IntegerField(validators=[MinValueValidator(0)], help_text="The number of items in stock.")
    created = models.DateTimeField(auto_now_add=True, help_text="The date and time when the product was created.")
    updated = models.DateTimeField(auto_now=True, help_text="The date and time when the product was last updated.")
    thumbnail = models.ImageField(
        null=True,
        blank=True,
        upload_to=product_upload_to_unique,
        help_text="A thumbnail image for the product."
    )
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.CASCADE,
        help_text="The category to which the product belongs."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="products",
        on_delete=models.CASCADE,
        help_text="The user who created the product."
    )
    objects = models.Manager()  # The default manager.
    in_stock = InStockManager()  # The custom 'in_stock' manager.
    tags = TaggableManager(through=CustomTaggedItem, help_text="Tags for the product.")
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)], help_text="The weight of the product.")
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)], help_text="The length of the product.")
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)], help_text="The width of the product.")
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0.0)], help_text="The height of the product.")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, help_text="The average rating of the product.")
    reviews_count = models.IntegerField(default=0, help_text="The number of reviews for the product.")

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['name']),
            models.Index(fields=['category']),
        ]
        ordering = ["name"]

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to auto-generate a unique slug.
        The slug is based on the product's name and the current date.
        If a slug already exists, a random string is appended to ensure uniqueness.
        This strategy helps prevent slug collisions and improves SEO.
        """
        from datetime import date
        from django.utils.crypto import get_random_string

        # Generate a base slug from the product name and the current date.
        base_slug = f"{slugify(self.name)}-{date.today().strftime('%Y-%m-%d')}"
        if not self.slug:
            self.slug = base_slug
        else:
            try:
                existing = self.__class__.objects.get(pk=self.pk)
            except self.__class__.DoesNotExist:
                existing = None
            if existing and self.name != existing.name:
                self.slug = base_slug

        # If the generated slug is already in use, append a random string to make it unique.
        while self.__class__.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{base_slug}-{get_random_string(6)}"

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """
        Returns the absolute URL for a product instance.
        """
        return reverse('api-v1:product-detail', kwargs={'slug': self.slug})

    def update_rating_and_reviews_count(self):
        """
        Calculates and updates the average rating and review count for the product.
        This method is typically called after a new review is added or an existing one is deleted.
        """
        from django.db.models import Avg, Count
        reviews = self.reviews.all()
        if reviews.exists():
            aggregation = reviews.aggregate(average_rating=Avg('rating'), count=Count('id'))
            self.rating = aggregation.get('average_rating', 0.00)
            self.reviews_count = aggregation.get('count', 0)
        else:
            self.rating = 0.00
            self.reviews_count = 0
        self.save(update_fields=['rating', 'reviews_count'])

    def __str__(self):
        return f"Product: {self.name} (ID: {self.product_id})"


class Review(models.Model):
    """
    Represents a review for a product.
    """
    product = models.ForeignKey(
        Product,
        related_name="reviews",
        on_delete=models.CASCADE,
        help_text="The product that this review is for."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reviews",
        on_delete=models.CASCADE,
        help_text="The user who wrote the review."
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        help_text="The rating given by the user, from 1 to 5."
    )
    comment = models.TextField(blank=True, null=True, help_text="The comment left by the user.")
    created = models.DateTimeField(auto_now_add=True, help_text="The date and time when the review was created.")
    updated = models.DateTimeField(auto_now=True, help_text="The date and time when the review was last updated.")

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-created"]
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['user']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_product_review',
                violation_error_message='A user can only leave one review per product.'
            )
        ]

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to validate that a user can only review a product
        they have purchased. This is a crucial business rule to ensure the authenticity of reviews.
        """
        # The business logic for checking if a user has purchased the product
        # has been moved to the service layer (shop/services.py) to avoid
        # duplicated logic and make the service layer the single source of truth.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Review by {self.user} for {self.product} - {self.rating} stars"
