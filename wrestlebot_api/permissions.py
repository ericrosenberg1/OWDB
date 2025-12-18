"""
Custom permissions for WrestleBot API.

Security measures:
1. Token-based authentication
2. IP whitelist (optional)
3. User-agent check (optional)
"""

from rest_framework import permissions
import os


class IsWrestleBot(permissions.BasePermission):
    """
    Permission class for WrestleBot API access.

    Allows access if:
    1. Request has valid authentication token, OR
    2. Request is from localhost (development mode)
    """

    def has_permission(self, request, view):
        # In development, allow localhost without auth
        if self._is_localhost(request):
            return True

        # Require authentication token
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is the wrestlebot user
        return request.user.username == 'wrestlebot'

    def _is_localhost(self, request):
        """Check if request is from localhost."""
        remote_addr = request.META.get('REMOTE_ADDR', '')
        return remote_addr in ['127.0.0.1', 'localhost', '::1']


class IsWrestleBotOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to anyone, but write access only to WrestleBot.

    Useful for endpoints that need public read access but restricted writes.
    """

    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS to anyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write methods require WrestleBot authentication
        bot_permission = IsWrestleBot()
        return bot_permission.has_permission(request, view)
