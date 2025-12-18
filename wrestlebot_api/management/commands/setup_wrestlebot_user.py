"""
Management command to set up WrestleBot user and API token.

Usage:
    python manage.py setup_wrestlebot_user

This creates:
1. A 'wrestlebot' user account
2. An API authentication token
3. Displays the token for use in the standalone service
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
import secrets


class Command(BaseCommand):
    help = 'Set up WrestleBot user and API authentication token'

    def handle(self, *args, **options):
        User = get_user_model()

        # Create or get wrestlebot user
        user, created = User.objects.get_or_create(
            username='wrestlebot',
            defaults={
                'email': 'wrestlebot@localhost',
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
            }
        )

        if created:
            # Set a random password (not used for API auth)
            user.set_password(secrets.token_urlsafe(32))
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Created wrestlebot user'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'WrestleBot user already exists'
            ))

        # Create or get API token
        token, token_created = Token.objects.get_or_create(user=user)

        if token_created:
            self.stdout.write(self.style.SUCCESS(
                f'Created new API token'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'API token already exists'
            ))

        # Display the token
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('WrestleBot API Configuration'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(f'Username: {user.username}')
        self.stdout.write(f'API Token: {token.key}')
        self.stdout.write('')
        self.stdout.write('Add this to your .env file for the WrestleBot service:')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(f'WRESTLEBOT_API_TOKEN={token.key}'))
        self.stdout.write('')
        self.stdout.write('Or export as environment variable:')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(f'export WRESTLEBOT_API_TOKEN={token.key}'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

        # Test the API endpoint
        self.stdout.write('Test the API with:')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            f'curl -H "Authorization: Token {token.key}" http://localhost:8000/api/wrestlebot/status/'
        ))
        self.stdout.write('')
