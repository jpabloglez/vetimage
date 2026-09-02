"""
Clinic self-administration: the staff roster, role changes, offboarding, and
the clinic's own details.

Membership scopes access to every patient, study and report, so the tests that
matter are about what these operations must never do: destroy the clinical
record, hide it from the clinic that owns it, reach another clinic, or leave a
clinic with nobody who can administer it.
"""

import pytest
from django.contrib.auth import get_user_model

from conftest import TEST_PASSWORD
from users.models import CLINIC_ADMIN_ROLE, Clinic, UserProfile

User = get_user_model()

MEMBERS = '/users/clinic/members/'
PROFILE = '/users/clinic/profile/'


def _clinic(name, owner_email):
    owner = User.objects.create_user(email=owner_email, password=TEST_PASSWORD)
    return Clinic.objects.create(
        user=owner, name=name, address='', city='',
        billing_address='', billing_code='',
    )


def _member(email, clinic, role=1):
    u = User.objects.create_user(email=email, password=TEST_PASSWORD)
    u.role = role
    u.save(update_fields=['role'])
    p, _ = UserProfile.objects.get_or_create(user=u)
    p.clinic = clinic
    p.save()
    return u


@pytest.fixture
def clinic_a():
    return _clinic('Clinic A', 'owner-a@x.test')


@pytest.fixture
def clinic_b():
    return _clinic('Clinic B', 'owner-b@x.test')


@pytest.fixture
def admin_a(clinic_a):
    return _member('admin-a@x.test', clinic_a, role=CLINIC_ADMIN_ROLE)


@pytest.fixture
def vet_a(clinic_a):
    return _member('vet-a@x.test', clinic_a, role=1)


@pytest.mark.django_db
class TestRosterVisibility:

    def test_an_admin_sees_their_clinic_roster(self, api_client, admin_a, vet_a):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.get(MEMBERS)
        assert resp.status_code == 200
        emails = {row['email'] for row in resp.data['results']}
        assert emails == {'admin-a@x.test', 'vet-a@x.test'}

    def test_the_roster_stops_at_the_clinic_boundary(
        self, api_client, admin_a, clinic_b,
    ):
        _member('theirs@x.test', clinic_b, role=1)
        api_client.force_authenticate(user=admin_a)
        emails = {row['email'] for row in api_client.get(MEMBERS).data['results']}
        assert 'theirs@x.test' not in emails

    def test_a_vet_cannot_read_the_roster(self, api_client, vet_a):
        api_client.force_authenticate(user=vet_a)
        assert api_client.get(MEMBERS).status_code == 403

    def test_anonymous_cannot_read_the_roster(self, api_client):
        assert api_client.get(MEMBERS).status_code in (401, 403)


@pytest.mark.django_db
class TestOffboardingPreservesTheClinicalRecord:
    """
    The whole reason revocation deactivates rather than deletes or unlinks.
    """

    def test_revoking_does_not_delete_the_studies_they_uploaded(
        self, api_client, admin_a, clinic_a, study,
    ):
        """MedicalStudy.uploaded_by cascades, so deleting the account would
        take the clinic's imaging with it."""
        from dicom_images.models import MedicalStudy

        leaver = study.uploaded_by
        profile, _ = UserProfile.objects.get_or_create(user=leaver)
        profile.clinic = clinic_a
        profile.save()

        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(f'{MEMBERS}{leaver.id}/revoke/')
        assert resp.status_code == 200

        assert User.objects.filter(id=leaver.id).exists()
        assert MedicalStudy.objects.filter(id=study.id).exists()

    def test_the_clinic_keeps_seeing_their_studies(
        self, api_client, admin_a, clinic_a, study,
    ):
        """Scoping matches on uploaded_by__userprofile__clinic, so clearing the
        leaver's clinic would hide their studies from the clinic that owns
        them. Revocation must leave that link intact."""
        from dicom_images.scoping import visible_studies

        leaver = study.uploaded_by
        profile, _ = UserProfile.objects.get_or_create(user=leaver)
        profile.clinic = clinic_a
        profile.save()

        api_client.force_authenticate(user=admin_a)
        api_client.post(f'{MEMBERS}{leaver.id}/revoke/')

        profile.refresh_from_db()
        assert profile.clinic_id == clinic_a.id
        assert study in visible_studies(admin_a)

    def test_revoking_blocks_the_person_from_logging_in(
        self, api_client, admin_a, vet_a,
    ):
        api_client.force_authenticate(user=admin_a)
        api_client.post(f'{MEMBERS}{vet_a.id}/revoke/')

        vet_a.refresh_from_db()
        assert vet_a.is_active is False

        api_client.force_authenticate(user=None)
        resp = api_client.post(
            '/users/auth/login/',
            {'email': 'vet-a@x.test', 'password': TEST_PASSWORD}, format='json',
        )
        assert resp.status_code != 200

    def test_restoring_gives_access_back(self, api_client, admin_a, vet_a):
        api_client.force_authenticate(user=admin_a)
        api_client.post(f'{MEMBERS}{vet_a.id}/revoke/')
        api_client.post(f'{MEMBERS}{vet_a.id}/restore/')

        vet_a.refresh_from_db()
        assert vet_a.is_active is True


@pytest.mark.django_db
class TestTheClinicAlwaysKeepsAnAdministrator:
    """
    A clinic with no active administrator cannot invite, change a role, or edit
    its own details — recovering needs platform staff.
    """

    def test_you_cannot_revoke_your_own_access(self, api_client, admin_a):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(f'{MEMBERS}{admin_a.id}/revoke/')
        assert resp.status_code == 400
        admin_a.refresh_from_db()
        assert admin_a.is_active is True

    def test_a_sole_admin_cannot_step_down(self, api_client, admin_a, vet_a):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(f'{MEMBERS}{admin_a.id}/role/', {'role': 1}, format='json')
        assert resp.status_code == 400
        admin_a.refresh_from_db()
        assert admin_a.role == CLINIC_ADMIN_ROLE

    def test_stepping_down_works_once_someone_else_is_promoted(
        self, api_client, admin_a, vet_a,
    ):
        api_client.force_authenticate(user=admin_a)
        assert api_client.post(
            f'{MEMBERS}{vet_a.id}/role/', {'role': 3}, format='json',
        ).status_code == 200
        assert api_client.post(
            f'{MEMBERS}{admin_a.id}/role/', {'role': 1}, format='json',
        ).status_code == 200

        admin_a.refresh_from_db()
        vet_a.refresh_from_db()
        assert admin_a.role == 1
        assert vet_a.role == CLINIC_ADMIN_ROLE

    def test_demoting_another_admin_is_allowed(self, api_client, admin_a, clinic_a):
        """Safe by construction — the caller remains an administrator."""
        other = _member('admin-2@x.test', clinic_a, role=CLINIC_ADMIN_ROLE)
        api_client.force_authenticate(user=admin_a)
        assert api_client.post(
            f'{MEMBERS}{other.id}/role/', {'role': 1}, format='json',
        ).status_code == 200


@pytest.mark.django_db
class TestRoleChangesCannotEscalate:

    @pytest.mark.parametrize('role', [5, 6, 99])
    def test_unassignable_roles_are_rejected(self, api_client, admin_a, vet_a, role):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(f'{MEMBERS}{vet_a.id}/role/', {'role': role}, format='json')
        assert resp.status_code == 400
        vet_a.refresh_from_db()
        assert vet_a.role == 1

    def test_platform_access_is_not_reachable(self, api_client, admin_a, vet_a):
        api_client.force_authenticate(user=admin_a)
        api_client.post(
            f'{MEMBERS}{vet_a.id}/role/', {'role': 3, 'is_staff': True}, format='json',
        )
        vet_a.refresh_from_db()
        assert vet_a.is_staff is False

    def test_cannot_touch_a_member_of_another_clinic(
        self, api_client, admin_a, clinic_b,
    ):
        theirs = _member('theirs@x.test', clinic_b, role=1)
        api_client.force_authenticate(user=admin_a)
        assert api_client.post(
            f'{MEMBERS}{theirs.id}/role/', {'role': 3}, format='json',
        ).status_code == 404
        assert api_client.post(f'{MEMBERS}{theirs.id}/revoke/').status_code == 404

        theirs.refresh_from_db()
        assert theirs.role == 1
        assert theirs.is_active is True


@pytest.mark.django_db
class TestClinicProfile:

    def test_any_member_may_read_it(self, api_client, vet_a, clinic_a):
        api_client.force_authenticate(user=vet_a)
        resp = api_client.get(PROFILE)
        assert resp.status_code == 200
        assert resp.data['name'] == 'Clinic A'

    def test_only_an_admin_may_edit_it(self, api_client, vet_a):
        api_client.force_authenticate(user=vet_a)
        assert api_client.patch(PROFILE, {'name': 'Renamed'}, format='json').status_code == 403

    def test_an_admin_can_fix_an_auto_generated_name(
        self, api_client, admin_a, clinic_a,
    ):
        """Provisioned clinics are named after the email local part; this is
        how that gets corrected."""
        api_client.force_authenticate(user=admin_a)
        resp = api_client.patch(
            PROFILE,
            {'name': 'Clinica Veterinaria Norte', 'city': 'Madrid'},
            format='json',
        )
        assert resp.status_code == 200

        clinic_a.refresh_from_db()
        assert clinic_a.name == 'Clinica Veterinaria Norte'
        assert clinic_a.city == 'Madrid'

    def test_a_name_already_taken_is_rejected(self, api_client, admin_a, clinic_b):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.patch(PROFILE, {'name': 'clinic b'}, format='json')
        assert resp.status_code == 400

    def test_keeping_your_own_name_is_not_a_clash(self, api_client, admin_a, clinic_a):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.patch(
            PROFILE, {'name': 'Clinic A', 'city': 'Bilbao'}, format='json',
        )
        assert resp.status_code == 200

    def test_a_blank_name_is_rejected(self, api_client, admin_a):
        api_client.force_authenticate(user=admin_a)
        assert api_client.patch(PROFILE, {'name': '   '}, format='json').status_code == 400
