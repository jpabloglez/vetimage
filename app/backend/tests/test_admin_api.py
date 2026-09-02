"""
Platform-admin API.

This is the only surface in the codebase that reads across clinics, so the
tests that matter are the ones that keep the exception narrow: who may reach
it, that it exposes aggregates rather than clinical content, and that
registering a clinic never provisions an account under a customer's identity.
"""

import pytest
from django.contrib.auth import get_user_model

from conftest import TEST_PASSWORD, make_test_password
from users.models import Clinic, ClinicInvitation, UserProfile

User = get_user_model()

SUMMARY = '/api/admin/summary/'
STATS = '/api/admin/statistics/'
CLINICS = '/api/admin/clinics/'


def _clinic(name, owner_email):
    owner = User.objects.create_user(email=owner_email, password=TEST_PASSWORD)
    return Clinic.objects.create(
        user=owner, name=name, address='', city='',
        billing_address='', billing_code='',
    )


def _user(email, *, role=1, is_staff=False, clinic=None):
    u = User.objects.create_user(email=email, password=TEST_PASSWORD)
    u.role = role
    u.is_staff = is_staff
    u.save(update_fields=['role', 'is_staff'])
    p, _ = UserProfile.objects.get_or_create(user=u)
    p.clinic = clinic
    p.save()
    return u


@pytest.fixture
def platform_staff():
    return _user('staff@vetimage.app', is_staff=True)


@pytest.fixture
def clinic_a():
    return _clinic('Clinic A', 'owner-a@x.test')


@pytest.mark.django_db
class TestOnlyPlatformStaffMayRead:
    """
    Gated on is_staff, never on the clinical role. A Clinic Admin administers
    their own clinic; they are not VetImage staff, and the two axes must stay
    independent or 'admin' silently becomes cross-tenant access.
    """

    @pytest.mark.parametrize('url', [SUMMARY, STATS, CLINICS])
    def test_anonymous_is_refused(self, api_client, url):
        assert api_client.get(url).status_code in (401, 403)

    @pytest.mark.parametrize('url', [SUMMARY, STATS, CLINICS])
    def test_a_clinic_admin_is_refused(self, api_client, url, clinic_a):
        admin = _user('admin@x.test', role=3, clinic=clinic_a)
        api_client.force_authenticate(user=admin)
        assert api_client.get(url).status_code == 403

    @pytest.mark.parametrize('url', [SUMMARY, STATS, CLINICS])
    def test_platform_staff_may_read(self, api_client, url, platform_staff):
        api_client.force_authenticate(user=platform_staff)
        assert api_client.get(url).status_code == 200

    def test_a_clinic_admin_cannot_register_a_clinic(self, api_client, clinic_a):
        admin = _user('admin2@x.test', role=3, clinic=clinic_a)
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            CLINICS, {'name': 'Sneaky', 'admin_email': 'x@x.test'}, format='json',
        )
        assert resp.status_code == 403
        assert not Clinic.objects.filter(name='Sneaky').exists()


@pytest.mark.django_db
class TestRegisteringAClinic:

    def test_creates_the_clinic_and_invites_its_administrator(self, api_client, platform_staff):
        api_client.force_authenticate(user=platform_staff)
        resp = api_client.post(
            CLINICS,
            {'name': 'Norte', 'city': 'Madrid', 'admin_email': 'Director@Norte.test'},
            format='json',
        )
        assert resp.status_code == 201

        clinic = Clinic.objects.get(name='Norte')
        invitation = ClinicInvitation.objects.get(clinic=clinic)
        assert invitation.email == 'director@norte.test'
        assert invitation.role == 3
        assert resp.data['invitation_path'] == f'/invite/{invitation.token}'

    def test_does_not_create_an_account_for_the_customer(self, api_client, platform_staff):
        """
        Staff never hold a customer's password. Registration issues an
        invitation; the account appears only once the invitee redeems it.
        """
        api_client.force_authenticate(user=platform_staff)
        api_client.post(
            CLINICS, {'name': 'Sur', 'admin_email': 'director@sur.test'}, format='json',
        )
        assert not User.objects.filter(email='director@sur.test').exists()

    def test_the_invited_administrator_gets_no_platform_access(self, api_client, platform_staff):
        api_client.force_authenticate(user=platform_staff)
        api_client.post(
            CLINICS, {'name': 'Este', 'admin_email': 'director@este.test'}, format='json',
        )
        invitation = ClinicInvitation.objects.get(email='director@este.test')

        api_client.force_authenticate(user=None)
        api_client.post(
            f'/users/clinic/invitations/accept/{invitation.token}/',
            {'password': make_test_password('accept')}, format='json',
        )

        created = User.objects.get(email='director@este.test')
        assert created.role == 3            # admin of their own clinic
        assert created.is_staff is False    # but not of the platform
        assert created.userprofile.clinic.name == 'Este'

        api_client.force_authenticate(user=created)
        assert api_client.get(CLINICS).status_code == 403

    def test_duplicate_names_are_rejected(self, api_client, platform_staff):
        api_client.force_authenticate(user=platform_staff)
        first = api_client.post(
            CLINICS, {'name': 'Oeste', 'admin_email': 'a@x.test'}, format='json',
        )
        assert first.status_code == 201
        second = api_client.post(
            CLINICS, {'name': 'oeste', 'admin_email': 'b@x.test'}, format='json',
        )
        assert second.status_code == 400

    def test_cannot_move_someone_out_of_their_existing_clinic(
        self, api_client, platform_staff, clinic_a,
    ):
        """A profile carries one clinic, so inviting an existing member as the
        administrator of a new one would silently move them."""
        _user('taken@x.test', clinic=clinic_a)
        api_client.force_authenticate(user=platform_staff)
        resp = api_client.post(
            CLINICS, {'name': 'Nuevo', 'admin_email': 'taken@x.test'}, format='json',
        )
        assert resp.status_code == 400
        assert not Clinic.objects.filter(name='Nuevo').exists()


@pytest.mark.django_db
class TestRegistryCounts:

    def test_counts_do_not_multiply_across_joins(
        self, api_client, platform_staff, clinic_a, study,
    ):
        """
        Several counted paths fan out against one another. Without
        distinct=True two aggregates over the same multi-valued join multiply,
        so every figure on the page inflates.

        Needs more than one row on each side to catch it: 2 studies x 2 owners
        reads as 4 and 4 when the counts are not distinct.
        """
        from dicom_images.models import MedicalStudy
        from patients.models import Owner

        uploader = study.uploaded_by
        profile, _ = UserProfile.objects.get_or_create(user=uploader)
        profile.clinic = clinic_a
        profile.save()

        MedicalStudy.objects.create(
            study_instance_uid='1.2.3.admin.fanout',
            patient_name='X', patient_id='X',
            uploaded_by=uploader,
        )
        for i in range(2):
            Owner.objects.create(
                clinic=clinic_a, first_name=f'O{i}', last_name='T',
                email=f'o{i}@x.test', phone='600000000',
            )

        api_client.force_authenticate(user=platform_staff)
        rows = api_client.get(CLINICS).data['results']
        row = next(r for r in rows if r['id'] == clinic_a.id)

        assert row['studies_count'] == 2
        assert row['owners_count'] == 2
        assert row['members'] == 1

    def test_exposes_aggregates_not_clinical_content(
        self, api_client, platform_staff, clinic_a,
    ):
        api_client.force_authenticate(user=platform_staff)
        rows = api_client.get(CLINICS).data['results']
        assert rows, 'expected at least one clinic'

        allowed = {
            'id', 'name', 'address', 'city', 'created_at', 'founder_email',
            'members', 'owners_count', 'patients_count', 'studies_count',
            'analyses_count', 'last_activity',
        }
        assert set(rows[0].keys()) == allowed


@pytest.mark.django_db
class TestStatisticsWindow:

    def test_window_is_clamped(self, api_client, platform_staff):
        """An unbounded range would invite a full-table scan."""
        api_client.force_authenticate(user=platform_staff)
        assert api_client.get(f'{STATS}?days=99999').data['window_days'] == 365
        assert api_client.get(f'{STATS}?days=0').data['window_days'] == 1

    def test_junk_input_falls_back_instead_of_erroring(self, api_client, platform_staff):
        api_client.force_authenticate(user=platform_staff)
        resp = api_client.get(f'{STATS}?days=abc&clinic=xyz')
        assert resp.status_code == 200
        assert resp.data['window_days'] == 30

    def test_reports_the_shape_the_panel_renders(self, api_client, platform_staff):
        api_client.force_authenticate(user=platform_staff)
        data = api_client.get(STATS).data
        assert set(data) == {
            'window_days', 'since', 'totals', 'over_time',
            'by_model', 'by_clinic', 'by_status',
        }
        assert set(data['totals']) == {'total', 'succeeded', 'failed', 'success_rate'}

    def test_success_rate_is_none_rather_than_a_division_by_zero(
        self, api_client, platform_staff,
    ):
        api_client.force_authenticate(user=platform_staff)
        assert api_client.get(f'{STATS}?days=1').data['totals']['success_rate'] is None
