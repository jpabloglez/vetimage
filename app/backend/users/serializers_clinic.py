"""
Serializers for a Clinic Admin managing their own clinic: the staff roster and
the clinic's own details.

Membership is what scopes access to every patient, study and report, so these
are privilege operations. The constraints below are the security requirements,
not validation niceties.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CLINIC_ADMIN_ROLE, Clinic, UserProfile

User = get_user_model()

# Roles a Clinic Admin may assign, mirroring INVITABLE_ROLES: never 5
# (vestigial Superuser) or 6 (Pet Owner, who belong to the owner portal).
ASSIGNABLE_ROLES = (1, 3, 4)


class ClinicMemberSerializer(serializers.ModelSerializer):
    """One row of the clinic's staff roster."""

    email = serializers.EmailField(source='user.email', read_only=True)
    role = serializers.IntegerField(source='user.role', read_only=True)
    is_clinic_admin = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    last_login = serializers.DateTimeField(source='user.last_login', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            # No date_joined — this project's User model does not have one;
            # last_login is the only activity timestamp available.
            'user_id', 'email', 'first_name', 'last_name', 'role',
            'is_clinic_admin', 'is_active', 'last_login',
            'department', 'job_title',
        )
        read_only_fields = fields

    def get_is_clinic_admin(self, obj) -> bool:
        return obj.user.role == CLINIC_ADMIN_ROLE


class ClinicMemberRoleSerializer(serializers.Serializer):
    """Payload for changing a member's role."""

    role = serializers.IntegerField()

    def validate_role(self, value):
        if value not in ASSIGNABLE_ROLES:
            raise serializers.ValidationError('That role cannot be assigned.')
        return value


class ClinicProfileSerializer(serializers.ModelSerializer):
    """
    The clinic's own details, editable by its administrators.

    A clinic provisioned by `get_or_create_clinic` is named after the email
    local part ('jsmith'), which is nobody's clinic name — this is how that
    gets corrected.
    """

    class Meta:
        model = Clinic
        fields = (
            'id', 'name', 'address', 'city',
            'billing_address', 'billing_code', 'created_at',
        )
        read_only_fields = ('id', 'created_at')
        extra_kwargs = {
            'address': {'required': False, 'allow_blank': True},
            'city': {'required': False, 'allow_blank': True},
            'billing_address': {'required': False, 'allow_blank': True},
            'billing_code': {'required': False, 'allow_blank': True},
        }

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('A clinic name is required.')
        clash = Clinic.objects.filter(
            name__iexact=value, deleted_at__isnull=True,
        ).exclude(pk=self.instance.pk if self.instance else None)
        if clash.exists():
            raise serializers.ValidationError('A clinic with that name already exists.')
        return value
