from django.core.exceptions import ValidationError
from django.test import TestCase

from account.models import Address, Profile, UserAccount


class TestAccountModels(TestCase):
    def test_profile_str(self):
        user = UserAccount.objects.create_user(
            phone_number="+989111111111",
            username="profileuser",
            password="password123",
        )
        profile = Profile.objects.create(user=user)
        self.assertEqual(str(profile), "Profile of profileuser")

    def test_user_manager_create_user_requires_phone(self):
        with self.assertRaises(ValueError):
            UserAccount.objects.create_user(phone_number=None, password="password123")

    def test_user_manager_create_superuser_requires_staff(self):
        with self.assertRaises(ValueError):
            UserAccount.objects.create_superuser(
                phone_number="+989122222222",
                username="badstaff",
                password="password123",
                is_staff=False,
            )

    def test_user_manager_create_superuser_requires_superuser(self):
        with self.assertRaises(ValueError):
            UserAccount.objects.create_superuser(
                phone_number="+989133333333",
                username="badadmin",
                password="password123",
                is_superuser=False,
            )

    def test_user_account_name_and_str(self):
        user = UserAccount.objects.create_user(
            phone_number="+989144444444",
            username="nameuser",
            first_name="Test",
            last_name="User",
            password="password123",
        )
        self.assertEqual(user.name, "Test User")
        self.assertEqual(str(user), "nameuser")

    def test_user_account_username_validator(self):
        user = UserAccount(
            phone_number="+989155555555",
            username="invalid username!",
        )
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_user_account_phone_validator(self):
        user = UserAccount(
            phone_number="invalid-phone",
            username="validusername",
        )
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_address_str(self):
        user = UserAccount.objects.create_user(
            phone_number="+989166666666",
            username="addressuser",
            password="password123",
        )
        address = Address.objects.create(
            user=user,
            province="Tehran",
            city="Tehran",
            postal_code="1234567890",
            full_address="123 Example St",
            receiver_name="Receiver Name",
            receiver_phone="+989199999999",
        )
        self.assertEqual(str(address), "123 Example St, Tehran, Tehran")
