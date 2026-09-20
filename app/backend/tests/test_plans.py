"""
Subscription plan limits.

The tests that matter here are the ones about what a limit must *not* do. A
clinic over its seat count or past its monthly quota is blocked from starting
new work — it is never cut off from records it already has. Patient history is
a clinical and legal obligation, and a subscription state must not stand
between a vet and a chart.

The rest pins the two counting rules that are easy to get wrong: a revoked
member frees their seat (offboarding deactivates rather than deletes, so
counting rows would mean you keep paying for people who left), and a pending
invitation occupies one (or a clinic invites past its limit and finds out only
when colleagues start being turned away).
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conftest import TEST_PASSWORD
from users import plans
from users.models import CLINIC_ADMIN_ROLE, Clinic, ClinicInvitation, Plan, UserProfile

User = get_user_model()

INVITATIONS = '/users/clinic/invitations/'
USAGE = '/users/clinic/usage/'


@pytest.fixture
def solo_plan(db):
    return Plan.objects.create(
        slug='solo', name='Solo', seat_limit=2,
        monthly_analysis_quota=3, storage_bytes=1024,
        features=[Plan.FEATURE_STUDY_SHARING],
    )


@pytest.fixture
def unlimited_plan(db):
    return Plan.objects.create(
        slug='legacy', name='Legacy', seat_limit=None,
        monthly_analysis_quota=None, storage_bytes=None,
        is_public=False,
    )


def _clinic(name='Clinic A', plan=None):
    owner = User.objects.create_user(email=f'owner-{name}@x.test', password=TEST_PASSWORD)
    return Clinic.objects.create(
        user=owner, name=name, address='', city='',
        billing_address='', billing_code='', plan=plan,
    )


def _member(email, clinic, role=1, active=True):
    u = User.objects.create_user(email=email, password=TEST_PASSWORD)
    u.role = role
    u.is_active = active
    u.save(update_fields=['role', 'is_active'])
    profile, _ = UserProfile.objects.get_or_create(user=u)
    profile.clinic = clinic
    profile.save()
    return u


@pytest.mark.django_db
class TestSeatsAreCountedHonestly:

    def test_a_revoked_member_frees_their_seat(self, solo_plan):
        """
        Offboarding deactivates rather than deletes, so counting rows would
        mean a clinic keeps paying for everyone who ever left.
        """
        clinic = _clinic(plan=solo_plan)
        _member('stays@x.test', clinic)
        left = _member('left@x.test', clinic)
        assert plans.seats_used(clinic) == 2

        left.is_active = False
        left.save(update_fields=['is_active'])
        assert plans.seats_used(clinic) == 1

    def test_a_pending_invitation_occupies_a_seat(self, solo_plan):
        clinic = _clinic(plan=solo_plan)
        _member('one@x.test', clinic)
        ClinicInvitation.objects.create(
            clinic=clinic, email='incoming@x.test', role=1,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )
        assert plans.seat_refusal(clinic) is not None

    def test_a_revoked_invitation_does_not(self, solo_plan):
        clinic = _clinic(plan=solo_plan)
        _member('one@x.test', clinic)
        ClinicInvitation.objects.create(
            clinic=clinic, email='gone@x.test', role=1,
            expires_at=timezone.now() + timezone.timedelta(days=7),
            revoked_at=timezone.now(),
        )
        assert plans.seat_refusal(clinic) is None

    def test_an_expired_invitation_does_not(self, solo_plan):
        clinic = _clinic(plan=solo_plan)
        _member('one@x.test', clinic)
        ClinicInvitation.objects.create(
            clinic=clinic, email='stale@x.test', role=1,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        assert plans.seat_refusal(clinic) is None


@pytest.mark.django_db
class TestTheSeatLimitIsEnforcedWhereItIsFelt:

    def test_inviting_past_the_limit_is_refused(self, api_client, solo_plan):
        """
        Refused at the invitation, not at acceptance: the alternative is
        telling a colleague who was invited that they cannot come in.
        """
        clinic = _clinic(plan=solo_plan)
        admin = _member('admin@x.test', clinic, role=CLINIC_ADMIN_ROLE)
        _member('second@x.test', clinic)

        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            INVITATIONS, {'email': 'third@x.test', 'role': 1}, format='json',
        )
        assert resp.status_code == 402
        assert resp.data['code'] == 'plan_seat_limit'
        assert not ClinicInvitation.objects.filter(email='third@x.test').exists()

    def test_inviting_within_the_limit_still_works(self, api_client, solo_plan):
        clinic = _clinic(plan=solo_plan)
        admin = _member('admin@x.test', clinic, role=CLINIC_ADMIN_ROLE)

        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            INVITATIONS, {'email': 'second@x.test', 'role': 1}, format='json',
        )
        assert resp.status_code == 201

    def test_a_clinic_with_no_plan_is_unlimited(self, api_client):
        """A clinic predating plans, or one a migration missed, keeps working."""
        clinic = _clinic(plan=None)
        admin = _member('admin@x.test', clinic, role=CLINIC_ADMIN_ROLE)
        for i in range(5):
            _member(f'v{i}@x.test', clinic)

        api_client.force_authenticate(user=admin)
        assert api_client.post(
            INVITATIONS, {'email': 'more@x.test', 'role': 1}, format='json',
        ).status_code == 201


@pytest.mark.django_db
class TestLimitsNeverReachBackwards:
    """
    The line this feature must not cross. Being over a limit stops new work; it
    does not withdraw access to what is already there.
    """

    def test_being_over_the_seat_limit_does_not_lock_anyone_out(
        self, api_client, solo_plan,
    ):
        clinic = _clinic(plan=solo_plan)
        admin = _member('admin@x.test', clinic, role=CLINIC_ADMIN_ROLE)
        for i in range(4):  # well past the limit of 2
            _member(f'v{i}@x.test', clinic)

        api_client.force_authenticate(user=admin)
        assert api_client.get('/users/clinic/members/').status_code == 200
        assert api_client.get('/users/clinic/profile/').status_code == 200

    def test_an_over_quota_clinic_can_still_read_its_studies(
        self, api_client, solo_plan, study,
    ):
        """
        The heart of it: a spent quota stops new analyses and nothing else.
        The clinic is put genuinely over the limit first — an earlier version
        of this asserted `refusal is None or study in visible(...)`, which is
        true whichever way the refusal goes and so tested nothing.
        """
        from dicom_images.scoping import visible_studies

        clinic = _clinic(plan=solo_plan)
        vet = study.uploaded_by
        profile, _ = UserProfile.objects.get_or_create(user=vet)
        profile.clinic = clinic
        profile.save()

        plan = clinic.plan
        plan.monthly_analysis_quota = 0
        plan.save(update_fields=['monthly_analysis_quota'])
        clinic.refresh_from_db()

        # Genuinely over the limit...
        assert plans.analysis_refusal(clinic) is not None
        # ...and the existing record is still there, and still readable.
        assert study in visible_studies(vet)
        api_client.force_authenticate(user=vet)
        # QIDO-RS study list — the endpoint the viewer reads existing work from.
        assert api_client.get('/api/dicom/dicom-web/studies').status_code == 200


@pytest.mark.django_db
class TestTheMonthlyQuota:

    def test_it_counts_only_this_calendar_month(self, solo_plan, analysis_task):
        """
        A calendar month, not a rolling window, so "resets on the 1st" is a
        true statement a customer can plan around.
        """
        clinic = _clinic(plan=solo_plan)
        profile, _ = UserProfile.objects.get_or_create(user=analysis_task.created_by)
        profile.clinic = clinic
        profile.save()

        assert plans.analyses_this_month(clinic) == 1

        # Backdate it out of the window.
        last_month = plans.month_start() - timezone.timedelta(days=1)
        type(analysis_task).objects.filter(pk=analysis_task.pk).update(
            created_at=last_month,
        )
        assert plans.analyses_this_month(clinic) == 0

    def test_refusal_explains_when_it_resets(self, solo_plan):
        clinic = _clinic(plan=solo_plan)
        plan = clinic.plan
        plan.monthly_analysis_quota = 0
        plan.save(update_fields=['monthly_analysis_quota'])

        refusal = plans.analysis_refusal(clinic)
        assert refusal and 'resets' in refusal

    def test_zero_means_none_not_unlimited(self, solo_plan):
        """
        The classic way this model goes wrong: 0 doubling as "unlimited" makes
        a misconfigured plan silently grant everything.
        """
        clinic = _clinic(plan=solo_plan)
        plan = clinic.plan
        plan.monthly_analysis_quota = 0
        plan.save(update_fields=['monthly_analysis_quota'])
        assert plans.analysis_refusal(clinic) is not None

        plan.monthly_analysis_quota = None
        plan.save(update_fields=['monthly_analysis_quota'])
        assert plans.analysis_refusal(clinic) is None


@pytest.mark.django_db
class TestFeatureFlags:

    def test_a_granted_feature_passes(self, solo_plan):
        clinic = _clinic(plan=solo_plan)
        assert plans.feature_refusal(clinic, Plan.FEATURE_STUDY_SHARING) is None

    def test_an_ungranted_one_is_refused_by_name(self, solo_plan):
        clinic = _clinic(plan=solo_plan)
        refusal = plans.feature_refusal(clinic, Plan.FEATURE_API_KEYS)
        assert refusal and 'Solo' in refusal

    def test_no_plan_grants_everything(self):
        clinic = _clinic(plan=None)
        assert plans.feature_refusal(clinic, Plan.FEATURE_API_KEYS) is None


@pytest.mark.django_db
class TestTheUsageEndpoint:

    def test_any_member_can_see_it(self, api_client, solo_plan):
        """
        Not admin-only: a vet who hits the quota should be able to see why
        without having to ask someone.
        """
        clinic = _clinic(plan=solo_plan)
        vet = _member('vet@x.test', clinic, role=1)

        api_client.force_authenticate(user=vet)
        resp = api_client.get(USAGE)
        assert resp.status_code == 200
        assert resp.data['plan']['slug'] == 'solo'
        assert resp.data['seats']['limit'] == 2
        assert resp.data['seats']['used'] == 1

    def test_unlimited_reports_a_null_limit_not_a_sentinel(
        self, api_client, unlimited_plan,
    ):
        clinic = _clinic(plan=unlimited_plan)
        vet = _member('vet@x.test', clinic, role=1)

        api_client.force_authenticate(user=vet)
        resp = api_client.get(USAGE)
        assert resp.data['seats']['limit'] is None
        assert resp.data['seats']['remaining'] is None
        assert resp.data['seats']['exceeded'] is False

    def test_anonymous_cannot_read_it(self, api_client):
        assert api_client.get(USAGE).status_code in (401, 403)

    def test_what_it_reports_agrees_with_what_is_enforced(
        self, api_client, solo_plan,
    ):
        """
        The panel and the gate must not disagree. They did: the report counted
        only members while the check also counted pending invitations, so it
        showed a free seat the API then refused to fill.
        """
        clinic = _clinic(plan=solo_plan)
        admin = _member('admin@x.test', clinic, role=CLINIC_ADMIN_ROLE)
        ClinicInvitation.objects.create(
            clinic=clinic, email='incoming@x.test', role=1,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )

        api_client.force_authenticate(user=admin)
        seats = api_client.get(USAGE).data['seats']

        # One member, one invitation out: the seat is spoken for.
        assert seats['used'] == 2
        assert seats['members'] == 1
        assert seats['pending_invitations'] == 1
        assert seats['exceeded'] is True
        # And that is exactly what the gate says.
        assert plans.seat_refusal(clinic) is not None


@pytest.mark.django_db
class TestTheSeededPlans:

    def test_seeding_is_idempotent(self):
        from django.core.management import call_command

        call_command('seed_plans', verbosity=0)
        first = Plan.objects.count()
        call_command('seed_plans', verbosity=0)
        assert Plan.objects.count() == first

    def test_legacy_is_unlimited_and_not_offered(self):
        from django.core.management import call_command

        call_command('seed_plans', verbosity=0)
        legacy = Plan.objects.get(slug='legacy')
        assert legacy.seat_limit is None
        assert legacy.monthly_analysis_quota is None
        # Existing clinics agreed to nothing, so nothing is taken from them —
        # but the tier is not offered to anyone new.
        assert legacy.is_public is False
@pytest.mark.django_db
class TestPlatformStaffAssignPlans:
    """
    Which tier a clinic is on is a commercial fact, so staff may set it —
    but that must not become a foothold for writing anything else.
    """

    @pytest.fixture
    def staff(self):
        u = User.objects.create_user(email='staff@vetimage.test', password=TEST_PASSWORD)
        u.is_staff = True
        u.save(update_fields=['is_staff'])
        return u

    def test_staff_can_move_a_clinic_to_another_plan(self, api_client, staff, solo_plan):
        clinic = _clinic(plan=None)
        api_client.force_authenticate(user=staff)

        resp = api_client.patch(
            f'/api/admin/clinics/{clinic.id}/', {'plan': solo_plan.id}, format='json',
        )
        assert resp.status_code == 200

        clinic.refresh_from_db()
        assert clinic.plan_id == solo_plan.id

    def test_patch_cannot_rewrite_anything_else(self, api_client, staff, solo_plan):
        """The read-only-over-clinical-data rule has to survive the new verb."""
        clinic = _clinic(name='Real Name', plan=None)
        api_client.force_authenticate(user=staff)

        api_client.patch(
            f'/api/admin/clinics/{clinic.id}/',
            {'plan': solo_plan.id, 'name': 'Renamed By Staff', 'city': 'Nowhere'},
            format='json',
        )
        clinic.refresh_from_db()
        assert clinic.name == 'Real Name'
        assert clinic.city == ''

    def test_a_clinic_admin_cannot_change_their_own_plan(self, api_client, solo_plan):
        """Otherwise a customer upgrades themselves for free."""
        clinic = _clinic(plan=solo_plan)
        admin = _member('admin@x.test', clinic, role=CLINIC_ADMIN_ROLE)
        api_client.force_authenticate(user=admin)

        resp = api_client.patch(
            f'/api/admin/clinics/{clinic.id}/', {'plan': None}, format='json',
        )
        assert resp.status_code == 403
