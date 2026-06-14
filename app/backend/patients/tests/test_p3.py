"""
Tests for P3 features: reproductive events, insurance fields,
breed-specific reference ranges, and the new vet AI connectors.
"""
import pytest


@pytest.mark.django_db
class TestReproductiveEventAPI:
    BASE = '/api/patients/reproductive/'

    def _make_animal(self, auth_client):
        o = auth_client.post('/api/patients/owners/', {
            'first_name': 'Repro', 'last_name': 'Owner',
            'email': 'repro@example.com', 'phone': '555-0021',
        }, format='json').data
        return auth_client.post('/api/patients/animals/', {
            'owner_id': o['id'], 'name': 'Bella', 'species': 'canine',
        }, format='json').data

    def test_create_event(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'event_type': 'mating',
            'event_date': '2026-02-01',
            'partner_id': 'CHIP-900000000000999',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['event_type'] == 'mating'

    def test_future_event_date_rejected(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'event_type': 'heat',
            'event_date': '2099-01-01',
        }, format='json')
        assert resp.status_code == 400

    def test_litter_count_optional(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'event_type': 'whelping',
            'event_date': '2026-03-01',
            'litter_count': 6,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['litter_count'] == 6

    def test_list_filtered_by_animal(self, auth_client):
        animal = self._make_animal(auth_client)
        auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'event_type': 'heat', 'event_date': '2026-01-01',
        }, format='json')
        resp = auth_client.get(f'{self.BASE}?animal={animal["id"]}')
        results = resp.data.get('results', resp.data)
        assert len(results) == 1

    def test_from_other_org_not_visible(self, auth_client, reproductive_event):
        resp = auth_client.get(self.BASE)
        ids = [e['id'] for e in (resp.data.get('results', resp.data))]
        assert reproductive_event.id not in ids


@pytest.mark.django_db
class TestInsuranceFields:
    def test_insurance_fields_persist(self, auth_client):
        o = auth_client.post('/api/patients/owners/', {
            'first_name': 'Ins', 'last_name': 'Owner',
            'email': 'ins@example.com', 'phone': '555-0022',
        }, format='json').data
        animal = auth_client.post('/api/patients/animals/', {
            'owner_id': o['id'], 'name': 'Rocky', 'species': 'canine',
            'insurance_provider': 'PetPlan',
            'insurance_policy_number': 'PP-12345',
            'insurance_expiry': '2027-01-01',
        }, format='json').data
        assert animal['insurance_provider'] == 'PetPlan'

        detail = auth_client.get(f'/api/patients/animals/{animal["id"]}/')
        assert detail.data['insurance_policy_number'] == 'PP-12345'
        assert detail.data['insurance_expiry'] == '2027-01-01'


@pytest.mark.django_db
class TestBreedReference:
    def test_lookup_breed_specific_wins(self, breed_reference):
        from patients.models import BreedReference
        ref = BreedReference.lookup('canine', 'Boxer mix', 'vhs')
        assert ref is not None
        assert ref['low'] == 9.8
        assert ref['high'] == 11.6

    def test_lookup_falls_back_to_species_wide(self, db):
        from patients.models import BreedReference
        BreedReference.objects.create(
            species='canine', breed_pattern='', metric='vhs', low='8.5', high='10.6',
        )
        ref = BreedReference.lookup('canine', 'Poodle', 'vhs')
        assert ref['low'] == 8.5

    def test_lookup_returns_none_when_no_match(self, db):
        from patients.models import BreedReference
        assert BreedReference.lookup('feline', 'Siamese', 'vhs') is None

    def test_vhs_interpretation_uses_breed_reference(self, animal_patient, user, breed_reference):
        """A Boxer's VHS of 11.0 is within the breed range but above the general range."""
        from decimal import Decimal
        from patients.models import VHSMeasurement
        animal_patient.species = 'canine'
        animal_patient.breed = 'Boxer'
        animal_patient.save(update_fields=['species', 'breed'])

        m = VHSMeasurement.objects.create(
            animal_patient=animal_patient,
            measured_on='2026-02-01',
            long_axis_vertebrae=Decimal('5.6'),
            short_axis_vertebrae=Decimal('5.4'),  # VHS = 11.0
            created_by=user,
        )
        # 11.0 is within the Boxer range (9.8–11.6), not above.
        assert m.interpretation == 'within_range'

    def test_vhs_interpretation_general_range_without_breed_ref(self, animal_patient, user):
        """Without a breed reference, a VHS of 11.0 is above the general canine range."""
        from decimal import Decimal
        from patients.models import VHSMeasurement
        animal_patient.species = 'canine'
        animal_patient.breed = 'Mixed'
        animal_patient.save(update_fields=['species', 'breed'])

        m = VHSMeasurement.objects.create(
            animal_patient=animal_patient,
            measured_on='2026-02-01',
            long_axis_vertebrae=Decimal('5.6'),
            short_axis_vertebrae=Decimal('5.4'),  # VHS = 11.0
            created_by=user,
        )
        assert m.interpretation == 'above_range'


@pytest.mark.django_db
class TestVetConnectorsSeeded:
    def test_hip_and_dental_models_instantiate(self):
        from django.core.management import call_command
        from ai_analysis.models import AIModel
        from ai_analysis.connectors.factory import ConnectorFactory

        call_command('seed_vet_models', '--keep-human', verbosity=0)

        for key, cls_name in [('vet-hip-v1', 'HipDysplasiaConnector'),
                              ('vet-dental-v1', 'VetDentalConnector')]:
            model = AIModel.objects.get(key=key)
            connector = ConnectorFactory.create(model)
            assert type(connector).__name__ == cls_name
            assert callable(getattr(connector, 'dispatch_job', None))


@pytest.mark.django_db
class TestPassportPDF:
    def _make_animal(self, auth_client, with_vaccination=True):
        o = auth_client.post('/api/patients/owners/', {
            'first_name': 'Pass', 'last_name': 'Port',
            'email': 'pp@example.com', 'phone': '555-0030',
        }, format='json').data
        animal = auth_client.post('/api/patients/animals/', {
            'owner_id': o['id'], 'name': 'Nube', 'species': 'feline',
            'microchip_id': '900000000000777',
        }, format='json').data
        if with_vaccination:
            auth_client.post('/api/patients/vaccinations/', {
                'animal_patient_id': animal['id'],
                'vaccine_name': 'Rabies',
                'administered_on': '2026-01-10',
                'next_due_on': '2027-01-10',
                'batch_number': 'LOT-X1',
            }, format='json')
        return animal

    def test_passport_returns_pdf(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.get(f'/api/patients/animals/{animal["id"]}/passport/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'
        assert resp.content.startswith(b'%PDF')
        assert 'attachment' in resp['Content-Disposition']

    def test_passport_works_without_vaccinations(self, auth_client):
        animal = self._make_animal(auth_client, with_vaccination=False)
        resp = auth_client.get(f'/api/patients/animals/{animal["id"]}/passport/')
        assert resp.status_code == 200
        assert resp.content.startswith(b'%PDF')

    def test_passport_cross_org_404(self, auth_client, animal_patient):
        # animal_patient fixture belongs to another organization
        resp = auth_client.get(f'/api/patients/animals/{animal_patient.id}/passport/')
        assert resp.status_code == 404
