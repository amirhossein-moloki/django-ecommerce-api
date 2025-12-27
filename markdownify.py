from django.utils.html import strip_tags


def markdownify(value, **_kwargs):
    if value is None:
        return ""
    return strip_tags(str(value))
