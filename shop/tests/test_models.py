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
        category = CategoryFactory(name="New Category")
        assert category.pk is not None
        assert category.slug == "new-category"


class TestProductModel:
    def test_product_creation_and_slug(self):
        product = ProductFactory(name="Cool Gadget")
        assert product.product_id is not None
        assert "cool-gadget" in product.slug

    def test_unique_slug_generation(self):
        product1 = ProductFactory(name="Same Name")
        product2 = ProductFactory(name="Same Name")
        assert product1.slug != product2.slug


class TestReviewModel:
    def test_unique_review_constraint(self):
        user = UserFactory()
        product = ProductFactory()
        ReviewFactory(user=user, product=product)
        with pytest.raises(IntegrityError):
            ReviewFactory(user=user, product=product)


class TestThumbnailValidator:
    def create_dummy_image(self, size_kb, image_format="jpeg"):
        image_file = io.BytesIO()
        image = Image.new("RGB", (100, 100), "white")
        image.save(image_file, image_format)
        while image_file.tell() < size_kb * 1024:
            image_file.write(b"\\0")
        image_file.seek(0)
        return image_file

    def test_thumbnail_max_size_validation(self):
        large_file_content = self.create_dummy_image(2049)  # > 2MB
        large_file = SimpleUploadedFile(
            "large_image.jpg", large_file_content.read(), content_type="image/jpeg"
        )
        product = ProductFactory()
        product.thumbnail = large_file
        with pytest.raises(ValidationError, match="File size cannot exceed 2MB."):
            product.full_clean()

    def test_thumbnail_content_type_validation(self):
        invalid_file = SimpleUploadedFile(
            "document.txt", b"some text", content_type="text/plain"
        )
        product = ProductFactory()
        product.thumbnail = invalid_file
        with pytest.raises(ValidationError, match="Unsupported file type: text/plain."):
            product.full_clean()


class TestRatingSignal:
    def test_update_product_rating_on_review_save_and_delete(self):
        product = ProductFactory()
        user1 = UserFactory()
        user2 = UserFactory()

        ReviewFactory(product=product, user=user1, rating=4)
        product.refresh_from_db()
        assert product.rating == 4.00
        assert product.reviews_count == 1

        review2 = ReviewFactory(product=product, user=user2, rating=5)
        product.refresh_from_db()
        assert product.rating == 4.50
        assert product.reviews_count == 2

        review2.delete()
        product.refresh_from_db()
        assert product.rating == 4.00
        assert product.reviews_count == 1
