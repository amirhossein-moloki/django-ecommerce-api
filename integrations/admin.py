from django.contrib import admin
from .models import IntegrationSettings

@admin.register(IntegrationSettings)
class IntegrationSettingsAdmin(admin.ModelAdmin):
    """
    Admin configuration for the IntegrationSettings model.
    """
    list_display = ('__str__', 'torob_enabled', 'emalls_enabled', 'feed_token')

    def has_add_permission(self, request):
        # Prevent adding new instances from the admin, enforcing the singleton pattern.
        return not IntegrationSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the settings object.
        return False
