"""
Platform-admin serializers.

These read across every clinic, so what they may expose is deliberately narrow:
aggregate counts, timestamps and the clinic's own identifying details — never
clinical content. Patient names, findings and images stay inside the clinic
that owns them; a platform admin counts studies, they do not read them.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CLINIC_ADMIN_ROLE, Clinic

User = get_user_model()


class AdminClinicSerializer(serializers.ModelSerializer):
    """
    One row of the clinic registry, with the usage counts annotated by the
    view. The counts are read off annotations rather than recomputed here — a
    property per row would issue a query per row per metric.
    """

    members = serializers.IntegerField(source='_members', read_only=True)
    owners_count = serializers.IntegerField(source='_owners', read_only=True)
    patients_count = serializers.IntegerField(source='_patients', read_only=True)
    studies_count = serializers.IntegerField(source='_studies', read_only=True)
    analyses_count = serializers.IntegerField(source='_analyses', read_only=True)
    founder_email = serializers.EmailField(source='user.email', read_only=True, default=None)
    last_activity = serializers.DateTimeField(source='_last_activity', read_only=True, default=None)

    class Meta:
        model = Clinic
        fields = (
            'id', 'name', 'address', 'city', 'created_at', 'founder_email',
            'members', 'owners_count', 'patients_count', 'studies_count',
            'analyses_count', 'last_activity',
        )
        read_only_fields = fields


class AdminClinicCreateSerializer(serializers.ModelSerializer):
    """
    Register a clinic and invite its first administrator.

    Platform staff never write into a clinic's clinical records, so registering
    one does *not* create an account on the customer's behalf: it creates the
    empty clinic and issues an invitation, which the recipient redeems with a
    password only they ever know.
    """

    admin_email = serializers.EmailField(write_only=True)

    class Meta:
        model = Clinic
        fields = ('id', 'name', 'address', 'city', 'billing_address', 'billing_code', 'admin_email')
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
        if Clinic.objects.filter(name__iexact=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError('A clinic with that name already exists.')
        return value

    def validate_admin_email(self, value):
        value = value.strip().lower()
        existing = User.objects.filter(email__iexact=value).first()
        if existing is not None:
            # Their profile carries exactly one clinic, so inviting them into a
            # second would move them out of the first.
            profile = getattr(existing, 'userprofile', None)
            if getattr(profile, 'clinic_id', None) is not None:
                raise serializers.ValidationError(
                    'That person already belongs to a clinic.'
                )
        return value


class AdminClinicDetailSerializer(AdminClinicSerializer):
    """A single clinic, plus its roster. Still aggregate-only."""

    staff = serializers.SerializerMethodField()

    class Meta(AdminClinicSerializer.Meta):
        fields = AdminClinicSerializer.Meta.fields + ('staff',)
        read_only_fields = fields

    def get_staff(self, obj) -> list:
        return [
            {
                'id': profile.user_id,
                'email': profile.user.email,
                'role': profile.user.role,
                'is_clinic_admin': profile.user.role == CLINIC_ADMIN_ROLE,
                'is_active': profile.user.is_active,
                # No date_joined: this project's User model does not have one.
                'last_login': profile.user.last_login,
            }
            for profile in obj.staff.select_related('user').order_by('user__email')
        ]
