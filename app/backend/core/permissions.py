"""
The two authorization gates that sit above ordinary clinic membership.

These are deliberately separate axes:

  role        what you do inside a clinic (Veterinarian, Clinic Admin, ...)
  is_staff    whether you work for the platform

A person can be both — a vet at a pilot clinic who also works on VetImage —
which is precisely why platform access is not another entry in the role enum.
"""

from rest_framework.permissions import BasePermission

from users.models import CLINIC_ADMIN_ROLE

__all__ = ['CLINIC_ADMIN_ROLE', 'IsPlatformStaff', 'IsClinicAdmin']


class IsPlatformStaff(BasePermission):
    """
    VetImage staff, allowed to read across every clinic.

    This is the single gate that crosses the tenant boundary. Everything else
    in the codebase scopes to one clinic (see `dicom_images.scoping`), so views
    using this permission are the only ones permitted to query unscoped — and
    read-only: staff never write into a clinic's records, so no clinical record
    can be created or approved under someone else's identity.

    Deliberately keyed on `is_staff` alone, not `is_superuser`: the latter
    implicitly grants every Django permission, which this needs none of.
    """

    message = 'This area is restricted to VetImage platform staff.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class IsClinicAdmin(BasePermission):
    """
    An administrator of their own clinic — may manage its membership.

    Grants nothing across clinics. An accepted invitation gives immediate
    access to every patient, study and report in that clinic, so keeping this
    to Clinic Admins means one accountable person decides who joins.
    """

    message = 'Only a clinic administrator can manage clinic membership.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return getattr(user, 'role', None) == CLINIC_ADMIN_ROLE

    def has_object_permission(self, request, view, obj):
        """Objects must additionally belong to the admin's own clinic."""
        profile = getattr(request.user, 'userprofile', None)
        clinic = getattr(profile, 'clinic', None)
        if clinic is None:
            return False
        return getattr(obj, 'clinic_id', None) == clinic.id
