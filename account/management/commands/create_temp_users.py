from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


class Command(BaseCommand):
    help = "Creates two temporary users for testing purposes."

    def handle(self, *args, **options):
        users_data = [
            {
                "username": "tempuser1",
                "password": "password123",
                "phone_number": "+11111111111",
                "first_name": "Temp",
                "last_name": "User1",
            },
            {
                "username": "tempuser2",
                "password": "password456",
                "phone_number": "+22222222222",
                "first_name": "Temp",
                "last_name": "User2",
            },
        ]

        for user_data in users_data:
            try:
                if not User.objects.filter(username=user_data["username"]).exists():
                    User.objects.create_user(
                        username=user_data["username"],
                        password=user_data["password"],
                        phone_number=user_data["phone_number"],
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"],
                        is_active=True,
                        is_profile_complete=True,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully created user: {user_data['username']}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"User {user_data['username']} already exists. Skipping."
                        )
                    )
            except IntegrityError as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error creating user {user_data['username']}: {e}"
                    )
                )
