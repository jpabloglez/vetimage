"""
Tests for the pet-owner portal (#21): role-gated dashboard aggregating the
owner's pets + shared reports, and clinic-side account provisioning.
"""
import uuid
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import User, PET_OWNER_ROLE


@pytest.fixture
def owner_account(owner):
    """A portal login (role=Pet Owner) whose email matches the `owner` fixture."""
    return User.objects.create_user(email=owner.email, password='OwnerPass123!', role=PET_OWNER_ROLE)


@pytest.fixture
def owner_client(owner_account):
    client = APIClient()
    client.force_authenticate(user=owner_account)
    return client


@pytest.mark.django_db
class TestOwnerPortalDashboard:
    URL = '/api/portal/dashboard/'

    def test_lists_owner_pets(self, owner_client, animal_patient):
        resp = owner_client.get(self.URL)
        assert resp.status_code == 200, resp.content
        names = [p['name'] for p in resp.data['pets']]
        assert 'Rex' in names
        assert resp.data['owner']['pet_count'] == len(resp.data['pets'])

    def test_pet_includes_vaccination_and_appointments(self, owner_client, vaccination_record, appointment):
        resp = owner_client.get(self.URL)
        pet = next(p for p in resp.data['pets'] if p['name'] == 'Rex')
        assert any(v['vaccine_name'] == 'Rabies' for v in pet['vaccinations'])
        assert len(pet['upcoming_appointments']) >= 1

    def test_does_not_leak_other_owners_pets(self, owner_client, animal_patient, organization):
        # A different owner's animal in the same org must not appear.
        from patients.models import Owner, AnimalPatient
        other = Owner.objects.create(
            organization=organization, first_name='Bob', last_name='Other',
            email='bob.other@example.com', phone='555-0999',
        )
        AnimalPatient.objects.create(owner=other, name='NotYours', species='feline')
        resp = owner_client.get(self.URL)
        names = [p['name'] for p in resp.data['pets']]
        assert 'NotYours' not in names

    def test_lists_shared_reports(self, owner_client, report, animal_patient):
        report.study.animal_patient = animal_patient
        report.study.save(update_fields=['animal_patient'])
        report.share_token = uuid.uuid4()
        report.approved_at = timezone.now()
        report.save(update_fields=['share_token', 'approved_at'])
        resp = owner_client.get(self.URL)
        titles = [r['title'] for r in resp.data['shared_reports']]
        assert report.title in titles
        assert resp.data['shared_reports'][0]['share_path'].startswith('/shared/')

    def test_unapproved_report_not_shown(self, owner_client, report, animal_patient):
        report.study.animal_patient = animal_patient
        report.study.save(update_fields=['animal_patient'])
        report.share_token = uuid.uuid4()  # shared but NOT approved
        report.approved_at = None
        report.save(update_fields=['share_token', 'approved_at'])
        resp = owner_client.get(self.URL)
        assert resp.data['shared_reports'] == []

    def test_vet_account_forbidden(self, auth_client, animal_patient):
        # role=1 (vet) must not reach the owner portal.
        resp = auth_client.get(self.URL)
        assert resp.status_code == 403

    def test_anonymous_forbidden(self):
        resp = APIClient().get(self.URL)
        assert resp.status_code in (401, 403)


@pytest.mark.django_db
class TestOwnerAccountProvision:
    def _url(self, owner_id):
        return f'/api/portal/owners/{owner_id}/account/'

    def test_clinic_creates_owner_account(self, auth_client):
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'New', 'last_name': 'Client',
            'email': 'new.client@example.com', 'phone': '555-0123',
        }, format='json').data
        resp = auth_client.post(self._url(owner['id']), {'password': 'StrongPass123!'}, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['role'] == PET_OWNER_ROLE
        assert User.objects.filter(email='new.client@example.com', role=PET_OWNER_ROLE).exists()

    def test_short_password_rejected(self, auth_client):
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'A', 'last_name': 'B', 'email': 'shortpw@example.com', 'phone': '555-0124',
        }, format='json').data
        resp = auth_client.post(self._url(owner['id']), {'password': 'short'}, format='json')
        assert resp.status_code == 400

    def test_duplicate_email_rejected(self, auth_client):
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'Dup', 'last_name': 'Licate', 'email': 'dup@example.com', 'phone': '555-0125',
        }, format='json').data
        auth_client.post(self._url(owner['id']), {'password': 'StrongPass123!'}, format='json')
        resp = auth_client.post(self._url(owner['id']), {'password': 'StrongPass123!'}, format='json')
        assert resp.status_code == 400

    def test_owner_in_other_org_404(self, auth_client, owner):
        # `owner` fixture belongs to a different organisation.
        resp = auth_client.post(self._url(owner.id), {'password': 'StrongPass123!'}, format='json')
        assert resp.status_code == 404
