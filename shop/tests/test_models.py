import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from PIL import Image
import io

from account.tests.factories import UserFactory
from shop.models import Product, Category, Review
from shop.tests.factories import CategoryFactory, ProductFactory, ReviewFactory

pytestmark = pytest.mark.django_db


class TestCategoryModel:
    def test_category_creation_and_slug(self):
        """
        Tests that a category is created successfully and its slug is auto-generated.
        """
        category = CategoryFactory(name="New Category")
        assert category.pk is not None
        assert category.slug == "new-category"


class TestProductModel:
    def test_product_creation_and_slug(self):
        """
        Tests that a product is created successfully and its slug is auto-generated.
        """
        product = ProductFactory(name="Cool Gadget")
        assert product.product_id is not None
        assert "cool-gadget" in product.slug

    def test_unique_slug_generation(self):
        """
        Tests that two products with the same name get unique slugs.
        """
        product1 = ProductFactory(name="Same Name")
        product2 = ProductFactory(name="Same Name")
        assert product1.slug != product2.slug

    def test_soft_delete_and_restore(self):
        """
        Tests the soft delete and restore functionality.
        """
        product = ProductFactory()
        assert Product.objects.count() == 1
        product.delete()
        assert Product.objects.count() == 0
        assert Product.all_objects.count() == 1
        product.restore()
        assert Product.objects.count() == 1


class TestReviewModel:
    def test_unique_review_constraint(self):
        """
        Tests the constraint that a user can only review a product once.
        """
        user = UserFactory()
        product = ProductFactory()
        ReviewFactory(user=user, product=product)
        with pytest.raises(IntegrityError):
            ReviewFactory(user=user, product=product)


class TestThumbnailValidator:
    def create_dummy_image(self, size_kb, image_format="jpeg"):
        """Creates an in-memory image for testing."""
        image_file = io.BytesIO()
        # Create a small image
        image = Image.new('RGB', (100, 100), 'white')
        # Fill file until it reaches the desired size
        image.save(image_file, image_format)
        while image_file.tell() < size_kb * 1024:
            image_file.write(b'\\0')
        image_file.seek(0)
        return image_file

    def test_thumbnail_max_size_validation(self):
        """
        Tests that a ValidationError is raised for a file larger than the max size.
        """
        large_file_content = self.create_dummy_image(2049) # > 2MB
        large_file = SimpleUploadedFile(
            "large_image.jpg", large_file_content.read(), content_type="image/jpeg"
        )
        product = ProductFactory.build(thumbnail=large_file)
        with pytest.raises(ValidationError, match="File size cannot exceed 2MB."):
            product.full_clean()

    def test_thumbnail_content_type_validation(self):
        """
        Tests that a ValidationError is raised for an unsupported file type.
        """
        invalid_file = SimpleUploadedFile(
            "document.txt", b"some text", content_type="text/plain"
        )
        product = ProductFactory.build(thumbnail=invalid_file)
        with pytest.raises(ValidationError, match="Unsupported file type: text/plain."):
            product.full_clean()

    def test_valid_thumbnail(self):
        """
        Tests that a valid thumbnail passes validation.
        """
        valid_image_content = self.create_dummy_image(1024) # 1MB
        valid_file = SimpleUploadedFile(
            "valid_image.jpg", valid_image_content.read(), content_type="image/jpeg"
        )
        try:
            product = ProductFactory(thumbnail=valid_file)
            product.full_clean()  # Should not raise ValidationError
        except ValidationError:
            pytest.fail("ValidationError was raised for a valid thumbnail.")


class TestRatingSignal:
    def test_update_product_rating_on_review_save_and_delete(self):
        """
        Tests that the product's rating and reviews_count are updated when
        a review is created or deleted.
        """
        product = ProductFactory()
        user1 = UserFactory()
        user2 = UserFactory()

        # Initial state
        assert product.rating == 0.00
        assert product.reviews_count == 0

        # Create first review
        ReviewFactory(product=product, user=user1, rating=4)
        product.refresh_from_db()
        assert product.rating == 4.00
        assert product.reviews_count == 1

        # Create second review
        review2 = ReviewFactory(product=product, user=user2, rating=5)
        product.refresh_from_db()
        assert product.rating == 4.50
        assert product.reviews_count == 2

        # Delete a review
        review2.delete()
        product.refresh_from_db()
        assert product.rating == 4.00
        assert product.reviews_count == 1
