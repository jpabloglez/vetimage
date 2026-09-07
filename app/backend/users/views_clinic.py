"""
Clinic self-administration: the staff roster, and the clinic's own details.

Restricted to Clinic Admins — membership is what scopes access to every
patient, study and report, so adding and removing people is a privilege
operation.

**Removing a member deactivates the account; it never deletes it, and never
unlinks it from the clinic.** Both alternatives lose data:

* `MedicalStudy.uploaded_by` cascades on delete, so deleting a departed vet's
  account would delete every study they ever uploaded.
* Scoping matches on `uploaded_by__userprofile__clinic`, so clearing their
  clinic would hide those same studies from the clinic that owns them.

Deactivating revokes the person's access completely — they cannot log in, and
their sessions are terminated — while the clinic keeps the clinical record
they authored, still attributed to them. It is also reversible, which a
deletion is not.
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsClinicAdmin
from patients.views import get_or_create_clinic

from .models import CLINIC_ADMIN_ROLE, UserProfile
from .serializers_clinic import (
    ClinicMemberRoleSerializer,
    ClinicMemberSerializer,
    ClinicProfileSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def _terminate_sessions(user):
    """
    Best-effort: end the person's live sessions so deactivation takes effect
    now rather than when their access token expires. A failure here must never
    leave the account still active, so it never propagates.
    """
    try:
        from credentials.models import UserSession

        for session in UserSession.objects.filter(user=user, is_active=True):
            session.terminate(reason='removed_from_clinic')
    except Exception:
        logger.warning('Could not terminate sessions for user %s', user.id, exc_info=True)


class ClinicMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """
    The clinic's staff roster, and the operations on it.

    The invariant to preserve is that a clinic always keeps at least one active
    administrator — one with none cannot invite anyone, change a role, or edit
    its own details, and recovering needs platform staff. Two rules hold it:

    * You cannot revoke your own access. Acting on another admin is always
      safe, because you remain; it is only self-action that can empty the seat.
    * You may step down from admin, but only while another active admin
      remains. This is the one path that could otherwise leave the clinic with
      nobody, so it is the one that is checked.
    """

    serializer_class = ClinicMemberSerializer
    permission_classes = [IsAuthenticated, IsClinicAdmin]
    lookup_field = 'user_id'

    def get_queryset(self):
        clinic = get_or_create_clinic(self.request.user)
        if clinic is None:
            return UserProfile.objects.none()
        return (
            UserProfile.objects.filter(clinic=clinic)
            .select_related('user')
            .order_by('-user__is_active', 'user__email')
        )

    def _other_active_admins(self, clinic, exclude_user_id):
        return User.objects.filter(
            userprofile__clinic=clinic,
            role=CLINIC_ADMIN_ROLE,
            is_active=True,
        ).exclude(id=exclude_user_id)

    def _guard_revoke(self, target):
        """Return an error Response, or None when the revocation is allowed."""
        if target.id == self.request.user.id:
            return Response(
                {'error': 'You cannot revoke your own access. Ask another '
                          'administrator in your clinic.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Revoking anyone else is safe for the invariant: the caller is
        # themselves an active administrator and remains one.
        return None

    def _guard_role(self, target, clinic, *, new_role):
        """Return an error Response, or None when the role change is allowed."""
        stepping_down = (
            target.id == self.request.user.id
            and target.role == CLINIC_ADMIN_ROLE
            and new_role != CLINIC_ADMIN_ROLE
        )
        if stepping_down and not self._other_active_admins(clinic, target.id).exists():
            return Response(
                {'error': 'You are the clinic\'s only administrator. Promote '
                          'someone else before stepping down, or the clinic '
                          'would be left with nobody who can manage it.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Demoting someone else is safe: the caller stays an administrator.
        return None

    @extend_schema(
        summary="Change a member's role",
        request=ClinicMemberRoleSerializer,
        responses={200: ClinicMemberSerializer, 400: OpenApiTypes.OBJECT},
        tags=['Clinic'],
    )
    @action(detail=True, methods=['post'], url_path='role')
    @transaction.atomic
    def set_role(self, request, user_id=None):
        profile = self.get_object()
        target = profile.user
        clinic = get_or_create_clinic(request.user)

        serializer = ClinicMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data['role']

        blocked = self._guard_role(target, clinic, new_role=new_role)
        if blocked is not None:
            return blocked

        target.role = new_role
        # is_staff is platform access and is never reachable from here.
        target.save(update_fields=['role'])

        logger.info(
            'Clinic admin %s set role of user %s to %s in clinic %s',
            request.user.id, target.id, new_role, clinic.id,
        )
        return Response(ClinicMemberSerializer(profile).data)

    @extend_schema(
        summary='Revoke a member\'s access to the clinic',
        responses={200: ClinicMemberSerializer, 400: OpenApiTypes.OBJECT},
        tags=['Clinic'],
    )
    @action(detail=True, methods=['post'], url_path='revoke')
    @transaction.atomic
    def revoke(self, request, user_id=None):
        """Deactivate the account. See the module docstring for why this is not
        a delete and not an unlink."""
        profile = self.get_object()
        target = profile.user
        clinic = get_or_create_clinic(request.user)

        blocked = self._guard_revoke(target)
        if blocked is not None:
            return blocked

        if target.is_active:
            target.is_active = False
            target.save(update_fields=['is_active'])
            _terminate_sessions(target)
            logger.info(
                'Clinic admin %s revoked access for user %s in clinic %s',
                request.user.id, target.id, clinic.id,
            )
        return Response(ClinicMemberSerializer(profile).data)

    @extend_schema(
        summary="Restore a previously revoked member",
        responses={200: ClinicMemberSerializer},
        tags=['Clinic'],
    )
    @action(detail=True, methods=['post'], url_path='restore')
    @transaction.atomic
    def restore(self, request, user_id=None):
        profile = self.get_object()
        target = profile.user
        if not target.is_active:
            target.is_active = True
            target.save(update_fields=['is_active'])
            logger.info(
                'Clinic admin %s restored access for user %s',
                request.user.id, target.id,
            )
        return Response(ClinicMemberSerializer(profile).data)


class ClinicProfileView(RetrieveUpdateAPIView):
    """The caller's own clinic. Readable by any member, editable by its admins."""

    serializer_class = ClinicProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT'):
            return [IsAuthenticated(), IsClinicAdmin()]
        return [IsAuthenticated()]

    def get_object(self):
        return get_or_create_clinic(self.request.user)

    def perform_update(self, serializer):
        clinic = serializer.save()
        logger.info(
            'User %s updated details for clinic %s', self.request.user.id, clinic.id,
        )
