"""
Clinic invitations.

Accepting one grants immediate access to every patient, study and report in the
clinic, so an invitation is a privilege grant. The assertions that matter are
about what it *cannot* do: reach another clinic, confer platform access, be
issued by a non-admin, or be redeemed twice.
"""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from conftest import TEST_PASSWORD, make_test_password
from users.models import Clinic, ClinicInvitation, UserProfile

User = get_user_model()
LIST = '/users/clinic/invitations/'


def _accept_url(token):
    return reverse('accept-invitation', kwargs={'token': token})


def _clinic(name, owner_email):
    owner = User.objects.create_user(email=owner_email, password=TEST_PASSWORD)
    return Clinic.objects.create(
        user=owner, name=name, address='', city='',
        billing_address='', billing_code='',
    )


def _member(email, clinic, role):
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
    return _member('admin-a@x.test', clinic_a, role=3)


@pytest.fixture
def vet_a(clinic_a):
    return _member('vet-a@x.test', clinic_a, role=1)


@pytest.mark.django_db
class TestOnlyClinicAdminsMayInvite:

    def test_veterinarian_cannot_invite(self, api_client, vet_a):
        """An invite is a privilege grant; a compromised vet account must not
        be able to add an attacker-controlled member."""
        api_client.force_authenticate(user=vet_a)
        resp = api_client.post(LIST, {'email': 'x@x.test', 'role': 1}, format='json')
        assert resp.status_code == 403

    def test_clinic_admin_can_invite(self, api_client, admin_a):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(LIST, {'email': 'new@x.test', 'role': 1}, format='json')
        assert resp.status_code == 201
        assert resp.data['status'] == 'pending'
        assert resp.data['accept_path'].startswith('/invite/')

    def test_anonymous_cannot_invite(self, api_client):
        assert api_client.post(LIST, {'email': 'x@x.test'}, format='json').status_code in (401, 403)


@pytest.mark.django_db
class TestInvitationCannotEscalate:

    def test_cannot_confer_platform_access(self, api_client, admin_a, clinic_a):
        """is_staff is never reachable through this path — otherwise inviting a
        colleague becomes a route into every other clinic's data."""
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(
            LIST, {'email': 'esc@x.test', 'role': 1, 'is_staff': True}, format='json',
        )
        assert resp.status_code == 201
        inv = ClinicInvitation.objects.get(email='esc@x.test')

        api_client.force_authenticate(user=None)
        api_client.post(_accept_url(inv.token), {'password': make_test_password('accept')}, format='json')
        created = User.objects.get(email='esc@x.test')
        assert created.is_staff is False
        assert created.is_superuser is False

    @pytest.mark.parametrize('role', [5, 6, 99])
    def test_non_invitable_roles_are_rejected(self, api_client, admin_a, role):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(LIST, {'email': 'x@x.test', 'role': role}, format='json')
        assert resp.status_code == 400

    def test_clinic_comes_from_the_inviter_not_the_payload(self, api_client, admin_a, clinic_a, clinic_b):
        """Otherwise an admin could invite themselves into another clinic."""
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(
            LIST, {'email': 'x@x.test', 'role': 1, 'clinic': clinic_b.id}, format='json',
        )
        assert resp.status_code == 201
        assert ClinicInvitation.objects.get(email='x@x.test').clinic_id == clinic_a.id

    def test_role_on_the_account_comes_from_the_invitation(self, api_client, admin_a):
        """Not from the acceptance payload."""
        api_client.force_authenticate(user=admin_a)
        api_client.post(LIST, {'email': 'r@x.test', 'role': 4}, format='json')
        inv = ClinicInvitation.objects.get(email='r@x.test')

        api_client.force_authenticate(user=None)
        api_client.post(
            _accept_url(inv.token),
            {'password': make_test_password('accept'), 'role': 3}, format='json',
        )
        assert User.objects.get(email='r@x.test').role == 4


@pytest.mark.django_db
class TestTokenLifecycle:

    def _invite(self, api_client, admin, email='inv@x.test'):
        api_client.force_authenticate(user=admin)
        api_client.post(LIST, {'email': email, 'role': 1}, format='json')
        api_client.force_authenticate(user=None)
        return ClinicInvitation.objects.get(email=email)

    def test_accept_creates_the_member_in_the_right_clinic(self, api_client, admin_a, clinic_a):
        inv = self._invite(api_client, admin_a)
        resp = api_client.post(
            _accept_url(inv.token),
            {'password': make_test_password('accept'), 'first_name': 'New', 'last_name': 'Vet'},
            format='json',
        )
        assert resp.status_code == 201
        created = User.objects.get(email='inv@x.test')
        assert created.userprofile.clinic_id == clinic_a.id
        assert created.userprofile.first_name == 'New'

    def test_token_is_single_use(self, api_client, admin_a):
        inv = self._invite(api_client, admin_a)
        first = api_client.post(_accept_url(inv.token), {'password': make_test_password('accept')}, format='json')
        assert first.status_code == 201
        again = api_client.post(_accept_url(inv.token), {'password': make_test_password('accept')}, format='json')
        assert again.status_code == 404

    def test_expired_token_is_refused(self, api_client, admin_a):
        inv = self._invite(api_client, admin_a)
        inv.expires_at = timezone.now() - timedelta(minutes=1)
        inv.save(update_fields=['expires_at'])
        assert api_client.get(_accept_url(inv.token)).status_code == 404
        assert api_client.post(
            _accept_url(inv.token), {'password': make_test_password('accept')}, format='json',
        ).status_code == 404

    def test_revoked_token_is_refused(self, api_client, admin_a):
        inv = self._invite(api_client, admin_a)
        api_client.force_authenticate(user=admin_a)
        assert api_client.delete(f'{LIST}{inv.id}/').status_code == 204
        api_client.force_authenticate(user=None)
        assert api_client.get(_accept_url(inv.token)).status_code == 404

    def test_revoke_keeps_the_record_for_audit(self, api_client, admin_a):
        inv = self._invite(api_client, admin_a)
        api_client.force_authenticate(user=admin_a)
        api_client.delete(f'{LIST}{inv.id}/')
        inv.refresh_from_db()
        assert inv.revoked_at is not None
        assert inv.status == 'revoked'

    def test_unknown_token_is_refused(self, api_client):
        assert api_client.get(_accept_url(uuid.uuid4())).status_code == 404

    def test_public_lookup_reveals_only_the_clinic(self, api_client, admin_a):
        """No hint about whether an account already exists for the address."""
        inv = self._invite(api_client, admin_a)
        resp = api_client.get(_accept_url(inv.token))
        assert resp.status_code == 200
        assert set(resp.data.keys()) == {'clinic_name', 'email', 'expires_at'}

    def test_weak_password_is_rejected(self, api_client, admin_a):
        inv = self._invite(api_client, admin_a)
        assert api_client.post(
            _accept_url(inv.token), {'password': '123'}, format='json',
        ).status_code == 400
        assert not User.objects.filter(email='inv@x.test').exists()


@pytest.mark.django_db
class TestClinicIsolation:

    def test_admin_sees_only_their_own_clinics_invitations(
        self, api_client, admin_a, clinic_a, clinic_b,
    ):
        ClinicInvitation.objects.create(clinic=clinic_b, email='theirs@x.test', role=1)
        api_client.force_authenticate(user=admin_a)
        api_client.post(LIST, {'email': 'mine@x.test', 'role': 1}, format='json')

        emails = [row['email'] for row in api_client.get(LIST).data['results']]
        assert 'mine@x.test' in emails
        assert 'theirs@x.test' not in emails

    def test_admin_cannot_revoke_another_clinics_invitation(
        self, api_client, admin_a, clinic_b,
    ):
        theirs = ClinicInvitation.objects.create(
            clinic=clinic_b, email='theirs@x.test', role=1,
        )
        api_client.force_authenticate(user=admin_a)
        assert api_client.delete(f'{LIST}{theirs.id}/').status_code == 404
        theirs.refresh_from_db()
        assert theirs.revoked_at is None


@pytest.mark.django_db
class TestDuplicateGuards:

    def test_cannot_invite_an_existing_member(self, api_client, admin_a, vet_a):
        api_client.force_authenticate(user=admin_a)
        resp = api_client.post(LIST, {'email': vet_a.email, 'role': 1}, format='json')
        assert resp.status_code == 400

    def test_cannot_double_invite_while_pending(self, api_client, admin_a):
        api_client.force_authenticate(user=admin_a)
        assert api_client.post(LIST, {'email': 'dup@x.test', 'role': 1}, format='json').status_code == 201
        assert api_client.post(LIST, {'email': 'dup@x.test', 'role': 1}, format='json').status_code == 400

    def test_can_reinvite_after_revoking(self, api_client, admin_a):
        api_client.force_authenticate(user=admin_a)
        api_client.post(LIST, {'email': 're@x.test', 'role': 1}, format='json')
        inv = ClinicInvitation.objects.get(email='re@x.test')
        api_client.delete(f'{LIST}{inv.id}/')
        assert api_client.post(LIST, {'email': 're@x.test', 'role': 1}, format='json').status_code == 201


@pytest.mark.django_db
class TestClinicFoundersCanAdminister:
    """
    A clinic is provisioned lazily for whoever first touches clinic-scoped data.
    If that founder is not made its administrator, the clinic has nobody who can
    invite anyone — the panel is hidden from the one person who owns it.
    """

    def test_provisioning_a_clinic_makes_the_founder_its_admin(self, api_client):
        from patients.views import get_or_create_clinic

        founder = User.objects.create_user(email='founder@x.test', password=TEST_PASSWORD)
        assert founder.role == 1

        clinic = get_or_create_clinic(founder)

        founder.refresh_from_db()
        assert founder.role == 3
        assert clinic.user_id == founder.id

    def test_the_founder_can_then_invite(self, api_client):
        from patients.views import get_or_create_clinic

        founder = User.objects.create_user(email='founder2@x.test', password=TEST_PASSWORD)
        get_or_create_clinic(founder)
        founder.refresh_from_db()

        api_client.force_authenticate(user=founder)
        resp = api_client.post(LIST, {'email': 'colleague@x.test', 'role': 1}, format='json')
        assert resp.status_code == 201

    def test_joining_an_existing_clinic_does_not_promote(self, api_client, clinic_a, vet_a):
        """Only provisioning grants the role — never merely reading it back."""
        from patients.views import get_or_create_clinic

        assert vet_a.role == 1
        get_or_create_clinic(vet_a)

        vet_a.refresh_from_db()
        assert vet_a.role == 1

    def test_an_invited_member_is_not_promoted(self, api_client, admin_a, clinic_a):
        """The invitation's role is the whole grant; provisioning must not add to it."""
        from patients.views import get_or_create_clinic

        api_client.force_authenticate(user=admin_a)
        api_client.post(LIST, {'email': 'joiner@x.test', 'role': 1}, format='json')
        inv = ClinicInvitation.objects.get(email='joiner@x.test')

        api_client.force_authenticate(user=None)
        api_client.post(_accept_url(inv.token), {'password': make_test_password('accept')}, format='json')

        joiner = User.objects.get(email='joiner@x.test')
        get_or_create_clinic(joiner)
        joiner.refresh_from_db()
        assert joiner.role == 1
