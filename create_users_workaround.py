import os
import sys
from pathlib import Path

import dotenv


def main():
    """
    Workaround script to create temporary users.
    This script manually loads the .env file before setting up Django,
    bypassing the settings loading issue in manage.py.
    """
    # Add project root to the Python path
    current_dir = Path(__file__).resolve().parent
    sys.path.append(str(current_dir))

    # Load environment variables from .env file
    dotenv_path = current_dir / ".env"
    if dotenv_path.exists():
        print(f"Loading environment variables from {dotenv_path}")
        dotenv.load_dotenv(dotenv_path=dotenv_path)
    else:
        print(f"Warning: .env file not found at {dotenv_path}", file=sys.stderr)
        # Attempt to proceed, maybe env vars are set externally

    # Set the settings module and setup Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce_api.settings.development")

    try:
        import django
        from django.contrib.auth import get_user_model
        from django.db import IntegrityError

        print("Setting up Django...")
        django.setup()
        print("Django setup complete.")

        User = get_user_model()

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

        print("Starting user creation...")
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
                    print(f"Successfully created user: {user_data['username']}")
                else:
                    print(f"User {user_data['username']} already exists. Skipping.")
            except IntegrityError as e:
                print(f"Error creating user {user_data['username']}: {e}", file=sys.stderr)
            except Exception as e:
                print(f"An unexpected error occurred for user {user_data['username']}: {e}", file=sys.stderr)
        print("User creation process finished.")

    except ImportError as e:
        print(f"Failed to import Django or its components: {e}", file=sys.stderr)
        print("Please ensure Django and all project dependencies are installed.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during Django setup or user creation: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
