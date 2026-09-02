"""
Clinic invitation serializers.

The constraints here are the security requirements, not validation niceties:
an accepted invitation grants access to every patient, study and report in the
clinic, so what a Clinic Admin may put in one is deliberately narrow.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ClinicInvitation

User = get_user_model()

# Clinical roles an invitation may confer. Notably excludes 5 ("Superuser",
# vestigial) and 6 (Pet Owner, who belong to the owner portal, not clinic staff).
INVITABLE_ROLES = (1, 3, 4)


class ClinicInvitationSerializer(serializers.ModelSerializer):
    """Read/write shape for a Clinic Admin managing their clinic's invitations."""

    status = serializers.CharField(read_only=True)
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    accept_path = serializers.SerializerMethodField()

    class Meta:
        model = ClinicInvitation
        fields = (
            'id', 'email', 'role', 'status', 'created_at', 'expires_at',
            'accepted_at', 'invited_by_email', 'accept_path',
        )
        # clinic and invited_by come from the request, never the payload —
        # otherwise an admin could invite into someone else's clinic.
        read_only_fields = (
            'id', 'status', 'created_at', 'expires_at', 'accepted_at',
            'invited_by_email', 'accept_path',
        )

    def get_accept_path(self, obj) -> str:
        """Relative link the admin can copy. Full URL is built by the client so
        this stays correct behind any proxy or domain."""
        return f'/invite/{obj.token}'

    def validate_role(self, value):
        if value not in INVITABLE_ROLES:
            raise serializers.ValidationError(
                'That role cannot be granted by invitation.'
            )
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        clinic = self.context['clinic']

        if User.objects.filter(email__iexact=value, userprofile__clinic=clinic).exists():
            raise serializers.ValidationError('That person is already in this clinic.')

        pending = [
            inv for inv in ClinicInvitation.objects.filter(
                clinic=clinic, email__iexact=value,
            )
            if inv.is_pending
        ]
        if pending:
            raise serializers.ValidationError(
                'An invitation for that address is already pending.'
            )
        return value


class PublicInvitationSerializer(serializers.ModelSerializer):
    """
    What an unauthenticated visitor holding the token may see.

    Deliberately minimal: the clinic's name so they know what they are joining,
    and nothing that would confirm whether an account already exists for the
    address.
    """

    clinic_name = serializers.CharField(source='clinic.name', read_only=True)

    class Meta:
        model = ClinicInvitation
        fields = ('clinic_name', 'email', 'expires_at')
        read_only_fields = fields


class AcceptInvitationSerializer(serializers.Serializer):
    """Payload for redeeming an invitation."""

    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=80)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=80)

    def validate_password(self, value):
        validate_password(value)
        return value
