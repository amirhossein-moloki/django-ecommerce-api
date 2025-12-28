import os
import uuid
from django.utils.text import slugify


def get_sanitized_filename(filename):
    """
    Sanitizes a filename by removing special characters and ensuring a unique name.
    """
    name, ext = os.path.splitext(filename)
    sanitized_name = slugify(name)
    unique_id = uuid.uuid4().hex[:6]
    return f"{sanitized_name}-{unique_id}{ext}"
