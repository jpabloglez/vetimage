"""
Custom DRF permissions for credentials app
"""

from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners or admins to access objects.
    """

    def has_object_permission(self, request, view, obj):
        # Admin users have full access
        if request.user.is_staff or request.user.role >= 3:
            return True

        # Check if object has a user attribute and matches request user
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class IsAdminOrManager(permissions.BasePermission):
    """
    Permission to only allow admins or managers (role >= 2) to access.
    """

    def has_permission(self, request, view):
        # Check if user is staff or has manager/admin role
        return request.user.is_staff or request.user.role >= 2
