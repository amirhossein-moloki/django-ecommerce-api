import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from shop.validators import FileValidator


class TestFileValidator:
    def test_valid_file(self):
        validator = FileValidator(max_size=1024, content_types=("image/jpeg",))
        valid_file = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")

        # Should not raise an exception
        try:
            validator(valid_file)
        except ValidationError:
            pytest.fail("FileValidator raised ValidationError unexpectedly for a valid file.")

    def test_oversized_file(self):
        validator = FileValidator(max_size=1024, content_types=("image/jpeg",))
        oversized_file = SimpleUploadedFile("test.jpg", b"a" * 2048, content_type="image/jpeg")

        with pytest.raises(ValidationError) as excinfo:
            validator(oversized_file)
        assert "File size cannot exceed" in str(excinfo.value)

    def test_invalid_content_type(self):
        validator = FileValidator(max_size=1024, content_types=("image/png",))
        invalid_type_file = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")

        with pytest.raises(ValidationError) as excinfo:
            validator(invalid_type_file)
        assert "Unsupported file type" in str(excinfo.value)

    def test_content_type_guessed_from_name(self):
        validator = FileValidator(content_types=("image/jpeg",))
        # Create a file-like object and explicitly set its content_type to None
        # to force the validator to guess from the name.
        file_with_no_type = SimpleUploadedFile("test.jpg", b"file_content")
        file_with_no_type.content_type = None

        # This should pass as mimetype is guessed from 'test.jpg'
        try:
            validator(file_with_no_type)
        except ValidationError:
            pytest.fail("FileValidator failed to guess a valid MIME type.")

    def test_invalid_content_type_guessed(self):
        validator = FileValidator(content_types=("image/png",))
        file_with_invalid_guessed_type = SimpleUploadedFile("test.txt", b"file_content")
        file_with_invalid_guessed_type.content_type = None

        with pytest.raises(ValidationError) as excinfo:
            validator(file_with_invalid_guessed_type)
        assert "Unsupported file type" in str(excinfo.value)

    def test_no_restrictions(self):
        validator = FileValidator() # No max_size or content_types
        any_file = SimpleUploadedFile("any.anything", b"a" * 99999, content_type="application/octet-stream")

        # Should not raise an exception
        try:
            validator(any_file)
        except ValidationError:
            pytest.fail("FileValidator with no restrictions raised an unexpected error.")
