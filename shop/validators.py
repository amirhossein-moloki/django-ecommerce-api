import magic
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class FileValidator:
    """
    Validates files based on size and MIME type.
    """

    def __init__(self, max_size=None, content_types=()):
        self.max_size = max_size
        self.content_types = content_types

    def __call__(self, file):
        if self.max_size and file.size > self.max_size:
            raise ValidationError(
                f"File size cannot exceed {self.max_size / 1024 / 1024:.0f}MB."
            )

        if self.content_types:
            file_mime_type = magic.from_buffer(file.read(2048), mime=True)
            file.seek(0)  # Reset file pointer after reading
            if file_mime_type not in self.content_types:
                raise ValidationError(f"Unsupported file type: {file_mime_type}.")
