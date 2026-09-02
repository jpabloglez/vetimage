"""
Clinic invitation endpoints.

Two audiences, two very different permission stances:

  /api/clinic/invitations/            Clinic Admins, managing their own clinic
  /api/clinic/invitations/accept/<t>/ anonymous, holding the token

The accept endpoints are unauthenticated by necessity — the invitee has no
account yet — so the token has to carry the whole weight: single-use, expiring,
and throttled.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsClinicAdmin
from patients.views import get_or_create_clinic

from .models import ClinicInvitation, UserProfile
from .serializers_invitations import (
    AcceptInvitationSerializer,
    ClinicInvitationSerializer,
    PublicInvitationSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class ClinicInvitationViewSet(viewsets.ModelViewSet):
    """
    Manage invitations for the caller's own clinic.

    Restricted to Clinic Admins: accepting an invitation grants immediate
    access to every patient, study and report in the clinic, so one accountable
    person decides who joins.
    """

    serializer_class = ClinicInvitationSerializer
    permission_classes = [IsAuthenticated, IsClinicAdmin]
    throttle_scope = 'invitation'
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        clinic = get_or_create_clinic(self.request.user)
        if clinic is None:
            return ClinicInvitation.objects.none()
        return ClinicInvitation.objects.filter(clinic=clinic).select_related(
            'clinic', 'invited_by',
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['clinic'] = get_or_create_clinic(self.request.user)
        return ctx

    def perform_create(self, serializer):
        # clinic and inviter come from the request, never the payload.
        invitation = serializer.save(
            clinic=get_or_create_clinic(self.request.user),
            invited_by=self.request.user,
        )
        self._email_invitation(invitation)

    def perform_destroy(self, instance):
        """Revoke rather than delete, so the audit trail survives."""
        instance.revoked_at = timezone.now()
        instance.save(update_fields=['revoked_at'])

    def _email_invitation(self, invitation):
        """
        Best-effort. EMAIL_BACKEND defaults to the console backend, so this is
        a no-op in development — the admin copies `accept_path` from the UI
        instead. A mail failure must never lose the invitation itself.
        """
        base = getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')
        link = f'{base}/invite/{invitation.token}'
        try:
            send_mail(
                subject=f'You have been invited to join {invitation.clinic.name} on VetImage',
                message=(
                    f'{invitation.invited_by.email if invitation.invited_by else "A colleague"} '
                    f'has invited you to join {invitation.clinic.name} on VetImage.\n\n'
                    f'Accept the invitation: {link}\n\n'
                    f'This link expires on {invitation.expires_at:%d %B %Y} and can be used once.'
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@vetimage.app'),
                recipient_list=[invitation.email],
                fail_silently=True,
            )
        except Exception:
            logger.warning('Could not email invitation %s', invitation.id, exc_info=True)


class AcceptInvitationView(APIView):
    """
    GET  — what the invitee needs to render the acceptance page.
    POST — redeem the invitation and create the account.

    Unauthenticated: the invitee has no account yet.
    """

    permission_classes = [AllowAny]
    throttle_scope = 'invitation'

    def _pending(self, token):
        invitation = ClinicInvitation.objects.select_related('clinic').filter(
            token=token,
        ).first()
        if invitation is None or not invitation.is_pending:
            return None
        return invitation

    @extend_schema(
        summary='Look up a pending clinic invitation',
        responses={200: PublicInvitationSerializer, 404: OpenApiTypes.OBJECT},
        tags=['Authentication'],
    )
    def get(self, request, token):
        invitation = self._pending(token)
        if invitation is None:
            # One response for missing / expired / spent / revoked, so the
            # endpoint reveals nothing about which.
            return Response(
                {'error': 'This invitation is no longer valid.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PublicInvitationSerializer(invitation).data)

    @extend_schema(
        summary='Accept a clinic invitation and create the account',
        request=AcceptInvitationSerializer,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=['Authentication'],
    )
    @transaction.atomic
    def post(self, request, token):
        # Lock the row so two simultaneous redemptions can't both succeed.
        invitation = ClinicInvitation.objects.select_for_update().filter(
            token=token,
        ).select_related('clinic').first()
        if invitation is None or not invitation.is_pending:
            return Response(
                {'error': 'This invitation is no longer valid.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if User.objects.filter(email__iexact=invitation.email).exists():
            return Response(
                {'error': 'An account already exists for this address. Please sign in.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            email=invitation.email,
            password=serializer.validated_data['password'],
        )
        # role comes from the invitation, never from the request body — and
        # is_staff is never touched here, so an invitation can't become a route
        # into other clinics.
        user.role = invitation.role
        user.save(update_fields=['role'])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.clinic = invitation.clinic
        profile.email = invitation.email
        profile.first_name = serializer.validated_data.get('first_name', '') or ''
        profile.last_name = serializer.validated_data.get('last_name', '') or ''
        profile.save()

        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['accepted_at'])

        logger.info(
            'Invitation %s accepted; user %s joined clinic %s',
            invitation.id, user.id, invitation.clinic_id,
        )
        return Response(
            {'detail': 'Invitation accepted.', 'email': user.email},
            status=status.HTTP_201_CREATED,
        )
