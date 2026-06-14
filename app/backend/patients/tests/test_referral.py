"""
Tests for the referral network (#24): ReferringClinic directory,
ReferralPackage bundles, and the public token-gated landing endpoint.
"""
import pytest
from rest_framework.test import APIClient


def _rows(response):
    """Return the list of rows from a paginated or plain list response."""
    data = response.data
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


def _make_animal(auth_client):
    """Create an owner + animal inside the auth_client user's organisation."""
    o = auth_client.post('/api/patients/owners/', {
        'first_name': 'Ref', 'last_name': 'Erral',
        'email': 'ref@example.com', 'phone': '555-0200',
    }, format='json').data
    return auth_client.post('/api/patients/animals/', {
        'owner_id': o['id'], 'name': 'Scout', 'species': 'canine',
    }, format='json').data


@pytest.mark.django_db
class TestReferringClinic:
    BASE = '/api/patients/referring-clinics/'

    def test_create_and_list_clinic(self, auth_client):
        resp = auth_client.post(self.BASE, {
            'name': 'City Specialist Vets', 'contact_email': 'hi@csv.example',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['name'] == 'City Specialist Vets'

        listed = auth_client.get(self.BASE)
        names = [c['name'] for c in _rows(listed)]
        assert 'City Specialist Vets' in names

    def test_clinic_scoped_to_org(self, auth_client, organization):
        # A clinic in a *different* organisation must not appear in the list.
        from patients.models import ReferringClinic
        ReferringClinic.objects.create(organization=organization, name='Foreign Clinic')
        listed = auth_client.get(self.BASE)
        names = [c['name'] for c in _rows(listed)]
        assert 'Foreign Clinic' not in names


@pytest.mark.django_db
class TestReferralPackage:
    BASE = '/api/patients/referral-packages/'

    def test_create_package_generates_token(self, auth_client):
        animal = _make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'reason': 'Cardiology consult for suspected DCM.',
            'urgency': 'urgent',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['token']
        assert resp.data['share_path'] == f"/referral/{resp.data['token']}"
        assert resp.data['is_valid'] is True
        assert resp.data['animal_name'] == 'Scout'

    def test_create_links_study_by_uid(self, auth_client, study):
        animal = _make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'study_uid': study.study_instance_uid,
            'reason': 'See attached chest CT.',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['study_instance_uid'] == study.study_instance_uid

    def test_unknown_study_uid_rejected(self, auth_client):
        animal = _make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'study_uid': '9.9.9.does.not.exist',
        }, format='json')
        assert resp.status_code == 400

    def test_cross_org_animal_denied(self, auth_client, animal_patient):
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal_patient.id,  # belongs to another org
            'reason': 'x',
        }, format='json')
        assert resp.status_code == 403

    def test_list_filtered_by_animal(self, auth_client):
        a1 = _make_animal(auth_client)
        auth_client.post(self.BASE, {'animal_patient_id': a1['id'], 'reason': 'a'}, format='json')
        resp = auth_client.get(f"{self.BASE}?animal={a1['id']}")
        assert len(_rows(resp)) == 1


@pytest.mark.django_db
class TestPublicReferralEndpoint:
    def _create_pkg(self, auth_client, **extra):
        animal = _make_animal(auth_client)
        payload = {'animal_patient_id': animal['id'], 'reason': 'Ortho referral'}
        payload.update(extra)
        return auth_client.post('/api/patients/referral-packages/', payload, format='json').data

    def test_public_view_returns_sanitised_bundle(self, auth_client):
        pkg = self._create_pkg(auth_client, urgency='routine')
        anon = APIClient()  # no auth
        resp = anon.get(f"/api/patients/referrals/{pkg['token']}/")
        assert resp.status_code == 200, resp.content
        assert resp.data['patient']['name'] == 'Scout'
        assert resp.data['patient']['species'] == 'Canine'
        assert resp.data['reason'] == 'Ortho referral'
        assert resp.data['urgency'] == 'routine'
        assert 'disclaimer' in resp.data
        # No internal identifiers leak.
        assert 'id' not in resp.data
        assert 'created_by' not in resp.data

    def test_public_view_increments_access_count(self, auth_client):
        pkg = self._create_pkg(auth_client)
        anon = APIClient()
        anon.get(f"/api/patients/referrals/{pkg['token']}/")
        anon.get(f"/api/patients/referrals/{pkg['token']}/")
        from patients.models import ReferralPackage
        assert ReferralPackage.objects.get(token=pkg['token']).access_count == 2

    def test_public_view_unknown_token_404(self):
        anon = APIClient()
        resp = anon.get('/api/patients/referrals/00000000-0000-0000-0000-000000000000/')
        assert resp.status_code == 404

    def test_public_view_expired_404(self, auth_client):
        pkg = self._create_pkg(auth_client)
        from django.utils import timezone
        from patients.models import ReferralPackage
        obj = ReferralPackage.objects.get(token=pkg['token'])
        obj.expires_at = timezone.now() - timezone.timedelta(days=1)
        obj.save(update_fields=['expires_at'])
        anon = APIClient()
        resp = anon.get(f"/api/patients/referrals/{pkg['token']}/")
        assert resp.status_code == 404
