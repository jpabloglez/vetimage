"""
The platform-admin gate.

`is_staff` is the single boundary between an ordinary clinic user and read
access to every clinic's patient data, so the important assertions here are the
negative ones: it cannot be granted through the API, and the clinical `role`
field never confers it.
"""

import pytest
from conftest import make_test_password
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from core.permissions import CLINIC_ADMIN_ROLE, IsClinicAdmin, IsPlatformStaff

User = get_user_model()


class _Req:
    def __init__(self, user):
        self.user = user


@pytest.mark.django_db
class TestIsPlatformStaff:

    def test_ordinary_user_is_denied(self, user):
        assert IsPlatformStaff().has_permission(_Req(user), None) is False

    def test_staff_user_is_allowed(self, user):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        assert IsPlatformStaff().has_permission(_Req(user), None) is True

    @pytest.mark.parametrize('role', [1, 2, 3, 4, 5, 6])
    def test_no_clinical_role_grants_platform_access(self, user, role):
        """`role` describes clinic duties; it must never open the Admin area —
        including role 5 ('Superuser'), which is now a vestigial enum value."""
        user.role = role
        user.is_staff = False
        user.save(update_fields=['role', 'is_staff'])
        assert IsPlatformStaff().has_permission(_Req(user), None) is False

    def test_anonymous_is_denied(self):
        from django.contrib.auth.models import AnonymousUser
        assert IsPlatformStaff().has_permission(_Req(AnonymousUser()), None) is False


@pytest.mark.django_db
class TestIsClinicAdmin:

    def test_veterinarian_is_denied(self, user):
        user.role = 1
        user.save(update_fields=['role'])
        assert IsClinicAdmin().has_permission(_Req(user), None) is False

    def test_clinic_admin_is_allowed(self, user):
        user.role = CLINIC_ADMIN_ROLE
        user.save(update_fields=['role'])
        assert IsClinicAdmin().has_permission(_Req(user), None) is True

    def test_platform_staff_alone_does_not_grant_clinic_admin(self, user):
        """The two axes are independent in both directions."""
        user.role = 1
        user.is_staff = True
        user.save(update_fields=['role', 'is_staff'])
        assert IsClinicAdmin().has_permission(_Req(user), None) is False


@pytest.mark.django_db
class TestIsStaffIsNotSettableViaApi:

    def test_profile_patch_cannot_grant_staff(self, auth_client, user):
        """The obvious privilege-escalation route: ask nicely."""
        assert user.is_staff is False
        resp = auth_client.patch(
            reverse('profile'), {'is_staff': True}, format='json',
        )
        assert resp.status_code in (200, 202)
        assert resp.data['is_staff'] is False
        user.refresh_from_db()
        assert user.is_staff is False, 'is_staff must never be settable over the API'

    def test_profile_patch_cannot_self_promote_role(self, auth_client, user):
        """
        The profile view is a RetrieveUpdateAPIView, so any writable field is
        settable by the account itself. `role` was writable: a Veterinarian
        could PATCH themselves to Clinic Admin (3) and gain the right to invite
        members into the clinic.
        """
        assert user.role == 1
        resp = auth_client.patch(reverse('profile'), {'role': CLINIC_ADMIN_ROLE}, format='json')
        assert resp.status_code in (200, 202)
        assert resp.data['role'] == 1
        user.refresh_from_db()
        assert user.role == 1, 'role must never be settable by the account itself'

    def test_profile_patch_cannot_change_email(self, auth_client, user):
        """email is the USERNAME_FIELD; changing it freely is an
        account-takeover step (change address, then request a password reset)."""
        original = user.email
        resp = auth_client.patch(
            reverse('profile'), {'email': 'attacker@evil.test'}, format='json',
        )
        assert resp.status_code in (200, 202)
        user.refresh_from_db()
        assert user.email == original

    def test_profile_exposes_is_staff_read_only(self, auth_client):
        resp = auth_client.get(reverse('profile'))
        assert resp.status_code == 200
        assert 'is_staff' in resp.data
        assert 'clinic_name' in resp.data


@pytest.mark.django_db
class TestCreatePlatformAdminCommand:
    """Granting platform access requires shell access — there is no UI path."""

    def test_promotes_an_existing_account(self, user):
        call_command('create_platform_admin', user.email)
        user.refresh_from_db()
        assert user.is_staff is True

    def test_does_not_grant_django_superuser(self, user):
        """is_superuser implicitly grants every Django permission; the panel
        needs none of them."""
        call_command('create_platform_admin', user.email)
        user.refresh_from_db()
        assert user.is_superuser is False

    def test_does_not_change_the_clinical_role(self, user):
        before = user.role
        call_command('create_platform_admin', user.email)
        user.refresh_from_db()
        assert user.role == before

    def test_revoke(self, user):
        call_command('create_platform_admin', user.email)
        call_command('create_platform_admin', user.email, revoke=True)
        user.refresh_from_db()
        assert user.is_staff is False

    def test_creates_a_new_account_with_a_password(self):
        password = make_test_password('platform-admin')
        call_command('create_platform_admin', 'newadmin@vetimage.app', password=password)
        created = User.objects.get(email='newadmin@vetimage.app')
        assert created.is_staff is True
        assert created.is_superuser is False
        assert created.check_password(password)

    def test_revoking_an_unknown_account_errors(self):
        from django.core.management.base import CommandError
        with pytest.raises(CommandError):
            call_command('create_platform_admin', 'nobody@vetimage.app', revoke=True)
