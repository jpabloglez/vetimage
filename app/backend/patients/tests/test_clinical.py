"""
Tests for clinical visit, vaccination, weight, and appointment APIs.
All resources are scoped to the authenticated user's organization.
"""
import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestClinicalVisitAPI:
    BASE = '/api/patients/visits/'

    def _make_animal(self, auth_client):
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'Test', 'last_name': 'Owner',
            'email': 't@example.com', 'phone': '555-0001',
        }, format='json').data
        animal = auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Buddy', 'species': 'canine',
        }, format='json').data
        return owner, animal

    def test_create_visit(self, auth_client):
        _, animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'visit_date': '2026-03-01T10:00:00Z',
            'visit_type': 'consultation',
            'chief_complaint': 'Limping on left forelimb',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['chief_complaint'] == 'Limping on left forelimb'
        assert resp.data['visit_type'] == 'consultation'

    def test_soap_fields_optional(self, auth_client):
        _, animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'visit_date': '2026-03-01T09:00:00Z',
            'visit_type': 'follow_up',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['subjective'] == ''
        assert resp.data['assessment'] == ''

    def test_vital_signs_nullable(self, auth_client):
        _, animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'visit_date': '2026-03-01T08:00:00Z',
            'visit_type': 'consultation',
            'weight_kg': '32.5',
            'temperature_celsius': '38.5',
            'heart_rate_bpm': 80,
            'respiratory_rate': 20,
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['heart_rate_bpm'] == 80

    def test_invalid_temperature_rejected(self, auth_client):
        _, animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'visit_date': '2026-03-01T08:00:00Z',
            'visit_type': 'consultation',
            'temperature_celsius': '99',  # implausible
        }, format='json')
        assert resp.status_code == 400

    def test_list_visits_filtered_by_animal(self, auth_client):
        _, animal = self._make_animal(auth_client)
        auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'visit_date': '2026-03-01T10:00:00Z',
            'visit_type': 'consultation',
        }, format='json')
        resp = auth_client.get(f'{self.BASE}?animal={animal["id"]}')
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data)
        assert len(results) == 1

    def test_visit_from_other_org_not_visible(self, auth_client, clinical_visit):
        # clinical_visit belongs to a different org's animal (from fixture)
        resp = auth_client.get(self.BASE)
        results = resp.data.get('results', resp.data)
        ids = [v['id'] for v in results]
        assert clinical_visit.id not in ids


@pytest.mark.django_db
class TestVaccinationAPI:
    BASE = '/api/patients/vaccinations/'

    def _make_animal(self, auth_client):
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'Vax', 'last_name': 'Owner',
            'email': 'vax@example.com', 'phone': '555-0002',
        }, format='json').data
        return auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Luna', 'species': 'feline',
        }, format='json').data

    def test_create_vaccination_record(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'vaccine_name': 'Rabies',
            'administered_on': '2026-01-10',
            'next_due_on': '2027-01-10',
            'batch_number': 'LOT-2026A',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['vaccine_name'] == 'Rabies'
        assert resp.data['next_due_on'] == '2027-01-10'

    def test_next_due_date_optional(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'vaccine_name': 'Bordetella',
            'administered_on': '2026-01-10',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['next_due_on'] is None

    def test_future_administered_on_rejected(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'vaccine_name': 'Rabies',
            'administered_on': '2099-01-01',
        }, format='json')
        assert resp.status_code == 400

    def test_list_vaccinations_for_animal(self, auth_client):
        animal = self._make_animal(auth_client)
        for vaccine in ['Rabies', 'DHPPiL']:
            auth_client.post(self.BASE, {
                'animal_patient_id': animal['id'],
                'vaccine_name': vaccine,
                'administered_on': '2026-01-10',
            }, format='json')
        resp = auth_client.get(f'{self.BASE}?animal={animal["id"]}')
        results = resp.data.get('results', resp.data)
        assert len(results) == 2


@pytest.mark.django_db
class TestWeightAPI:
    BASE = '/api/patients/weights/'

    def _make_animal(self, auth_client):
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'Wt', 'last_name': 'Owner',
            'email': 'wt@example.com', 'phone': '555-0003',
        }, format='json').data
        return auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Max', 'species': 'canine',
        }, format='json').data

    def test_create_weight_record(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'measured_on': '2026-02-15',
            'weight_kg': '28.5',
            'bcs': 5,
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert float(resp.data['weight_kg']) == 28.5
        assert resp.data['bcs'] == 5

    def test_bcs_out_of_range_rejected(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'measured_on': '2026-02-15',
            'weight_kg': '28.5',
            'bcs': 10,  # invalid (>9)
        }, format='json')
        assert resp.status_code == 400

    def test_weight_trend_included_in_animal_detail(self, auth_client):
        animal = self._make_animal(auth_client)
        for w, d in [('28.0', '2026-01-01'), ('29.5', '2026-02-01')]:
            auth_client.post(self.BASE, {
                'animal_patient_id': animal['id'],
                'measured_on': d,
                'weight_kg': w,
            }, format='json')
        detail = auth_client.get(f'/api/patients/animals/{animal["id"]}/')
        assert detail.status_code == 200
        trend = detail.data.get('weight_trend', [])
        assert len(trend) == 2
        assert float(trend[0]['weight_kg']) == 28.0  # oldest first


@pytest.mark.django_db
class TestAppointmentAPI:
    BASE = '/api/patients/appointments/'

    def _make_animal(self, auth_client):
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'Apt', 'last_name': 'Owner',
            'email': 'apt@example.com', 'phone': '555-0004',
        }, format='json').data
        return auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Coco', 'species': 'canine',
        }, format='json').data

    def test_create_appointment(self, auth_client):
        animal = self._make_animal(auth_client)
        scheduled = (timezone.now() + timezone.timedelta(days=5)).isoformat()
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'appointment_type': 'consultation',
            'scheduled_at': scheduled,
            'duration_minutes': 45,
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['status'] == 'pending'
        assert resp.data['duration_minutes'] == 45

    def test_list_appointments_by_status(self, auth_client):
        animal = self._make_animal(auth_client)
        scheduled = (timezone.now() + timezone.timedelta(days=5)).isoformat()
        auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'appointment_type': 'consultation',
            'scheduled_at': scheduled,
        }, format='json')
        resp = auth_client.get(f'{self.BASE}?status=pending')
        results = resp.data.get('results', resp.data)
        assert all(a['status'] == 'pending' for a in results)

    def test_complete_creates_linked_visit(self, auth_client):
        animal = self._make_animal(auth_client)
        scheduled = (timezone.now() + timezone.timedelta(days=2)).isoformat()
        appt = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'appointment_type': 'follow_up',
            'scheduled_at': scheduled,
        }, format='json').data

        resp = auth_client.post(f'{self.BASE}{appt["id"]}/complete/', format='json')
        assert resp.status_code == 201, resp.content
        assert 'visit_id' in resp.data

        # Appointment should now be completed
        detail = auth_client.get(f'{self.BASE}{appt["id"]}/')
        assert detail.data['status'] == 'completed'
        assert detail.data['linked_visit'] == resp.data['visit_id']

    def test_complete_already_completed_returns_400(self, auth_client):
        animal = self._make_animal(auth_client)
        scheduled = (timezone.now() + timezone.timedelta(days=2)).isoformat()
        appt = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'appointment_type': 'consultation',
            'scheduled_at': scheduled,
        }, format='json').data
        auth_client.post(f'{self.BASE}{appt["id"]}/complete/', format='json')
        resp = auth_client.post(f'{self.BASE}{appt["id"]}/complete/', format='json')
        assert resp.status_code == 400

    def test_appointment_from_other_org_not_visible(self, auth_client, appointment):
        resp = auth_client.get(self.BASE)
        results = resp.data.get('results', resp.data)
        ids = [a['id'] for a in results]
        assert appointment.id not in ids
