import uuid
from django.db import models


class IntegrationSettings(models.Model):
    """
    A singleton model to store settings for third-party integrations like
    Torob and Emalls.
    """

    torob_enabled = models.BooleanField(
        default=False, help_text="Enable or disable the Torob XML feed."
    )
    emalls_enabled = models.BooleanField(
        default=False, help_text="Enable or disable the Emalls XML feed."
    )
    feed_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        help_text="Security token for accessing the feeds.",
    )

    class Meta:
        verbose_name = "Integration Settings"
        verbose_name_plural = "Integration Settings"

    def __str__(self):
        return "Integration Settings"

    def save(self, *args, **kwargs):
        """
        Ensure that only one instance of this model can be created.
        """
        if not self.pk and IntegrationSettings.objects.exists():
            raise ValueError("There can be only one IntegrationSettings instance.")
        return super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """
        Load the singleton instance, creating it if it doesn't exist.
        """
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
