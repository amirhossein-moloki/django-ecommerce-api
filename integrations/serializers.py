from rest_framework import serializers

class IntegrationToggleSerializer(serializers.Serializer):
    """
    Serializer for validating the toggle request for an integration.
    """
    name = serializers.ChoiceField(choices=['torob', 'emalls'])
    enabled = serializers.BooleanField()

    def update(self, instance, validated_data):
        """
        Updates the integration setting based on the validated data.
        """
        integration_name = validated_data.get('name')
        is_enabled = validated_data.get('enabled')

        if integration_name == 'torob':
            instance.torob_enabled = is_enabled
        elif integration_name == 'emalls':
            instance.emalls_enabled = is_enabled

        instance.save()
        return instance
