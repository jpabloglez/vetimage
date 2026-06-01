"""
Development Authentication Backend

WARNING: This is for DEVELOPMENT ONLY!
Accepts any token and creates a mock authenticated user.
DO NOT use in production!
"""

from rest_framework.authentication import BaseAuthentication
from .models import User


class DevelopmentTokenAuthentication(BaseAuthentication):
    """
    Development-only authentication that accepts any Bearer token.
    Creates or retrieves a development user for testing.
    """

    def authenticate(self, request):
        # Get Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            return None

        # Check if it's a Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]

        # Accept any token that starts with 'dev-token-'
        if not token.startswith('dev-token-'):
            return None

        # Get or create development user (using custom User model with email)
        user, created = User.objects.get_or_create(
            email='dev@example.com',
            defaults={
                'role': 1,  # User role
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
            }
        )

        # Set password if newly created
        if created:
            user.set_password('devpassword')
            user.save()

        # Return (user, auth) tuple
        # None for auth means no additional authentication object is needed
        return (user, None)

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'Bearer realm="api"'
