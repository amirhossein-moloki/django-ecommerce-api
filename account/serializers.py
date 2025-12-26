from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Profile, Address

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for the UserAccount model, including profile details."""

    profile_pic = serializers.ImageField(
        source="profile.profile_pic", required=False, use_url=True
    )
    balance = serializers.DecimalField(
        source="profile.balance", max_digits=10, decimal_places=2, read_only=True
    )
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "profile_pic",
            "balance",
            "password",
        )
        read_only_fields = ("id", "email", "phone_number", "balance")

    def update(self, instance, validated_data):
        # Update profile data if it exists
        if "profile" in validated_data:
            profile_data = validated_data.pop("profile")
            profile_instance = instance.profile
            for attr, value in profile_data.items():
                setattr(profile_instance, attr, value)
            profile_instance.save()

        # Update password if provided
        if "password" in validated_data:
            instance.set_password(validated_data["password"])
            validated_data.pop("password")

        # Update other user fields
        return super().update(instance, validated_data)


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True, help_text="Refresh token to be blacklisted"
    )


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "province",
            "city",
            "city_code",
            "postal_code",
            "full_address",
            "receiver_name",
            "receiver_phone",
        ]


class CompleteProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def update(self, instance, validated_data):
        instance.username = validated_data.get("username", instance.username)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.is_profile_complete = True
        instance.is_active = True
        instance.save()
        return instance
