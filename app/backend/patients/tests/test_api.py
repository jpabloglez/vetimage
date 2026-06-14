"""
API tests for the veterinary patients registry (Owner → AnimalPatient)
and study-to-patient linking.
"""
import pytest


@pytest.mark.django_db
class TestOwnerAPI:
    def test_create_owner_autoassigns_organization(self, auth_client):
        """A new user with no org can still create owners (org is provisioned)."""
        resp = auth_client.post('/api/patients/owners/', {
            'first_name': 'Maria', 'last_name': 'Lopez', 'email': 'm@example.com',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['first_name'] == 'Maria'
        assert resp.data['organization'] is not None

    def test_list_owners_scoped_to_org(self, auth_client, owner):
        """Owners from another organization are not visible."""
        # `owner` fixture belongs to a different org than auth_client's user.
        resp = auth_client.get('/api/patients/owners/')
        assert resp.status_code == 200
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        assert all(o['last_name'] != 'Smith' for o in results)

    def test_owner_requires_auth(self, api_client):
        resp = api_client.get('/api/patients/owners/')
        assert resp.status_code in (401, 403)


@pytest.mark.django_db
class TestAnimalAPI:
    def _make_owner(self, auth_client):
        return auth_client.post('/api/patients/owners/', {
            'first_name': 'Sam', 'last_name': 'Vet',
        }, format='json').data

    def test_create_and_get_animal(self, auth_client):
        owner = self._make_owner(auth_client)
        resp = auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Bella', 'species': 'feline',
            'breed': 'Siamese', 'sex': 'FS', 'weight_kg': '4.20',
        }, format='json')
        assert resp.status_code == 201, resp.content
        animal_id = resp.data['id']

        detail = auth_client.get(f'/api/patients/animals/{animal_id}/')
        assert detail.status_code == 200
        assert detail.data['name'] == 'Bella'
        assert detail.data['species'] == 'feline'
        assert detail.data['owner']['id'] == owner['id']
        assert detail.data['studies'] == []

    def test_microchip_must_be_unique_within_org(self, auth_client):
        owner = self._make_owner(auth_client)
        first = auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Rex', 'species': 'canine',
            'microchip_id': '900000000000123',
        }, format='json')
        assert first.status_code == 201, first.content
        dup = auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Max', 'species': 'canine',
            'microchip_id': '900000000000123',
        }, format='json')
        assert dup.status_code == 400
        assert 'microchip_id' in dup.data.get('details', dup.data)

    def test_invalid_microchip_rejected(self, auth_client):
        owner = self._make_owner(auth_client)
        resp = auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Rex', 'species': 'canine',
            'microchip_id': 'abc',  # too short / not ISO
        }, format='json')
        assert resp.status_code == 400
        assert 'microchip_id' in resp.data.get('details', resp.data)

    def test_filter_by_species(self, auth_client):
        owner = self._make_owner(auth_client)
        for name, sp in [('Rex', 'canine'), ('Whiskers', 'feline')]:
            auth_client.post('/api/patients/animals/', {
                'owner_id': owner['id'], 'name': name, 'species': sp,
            }, format='json')
        resp = auth_client.get('/api/patients/animals/?species=feline')
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        assert len(results) == 1
        assert results[0]['name'] == 'Whiskers'


@pytest.mark.django_db
class TestStudyLinking:
    def test_link_and_unlink_study_to_animal(self, auth_client, study):
        # study fixture is uploaded_by the auth_client user
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'Link', 'last_name': 'Owner',
        }, format='json').data
        animal = auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Scout', 'species': 'canine',
        }, format='json').data

        uid = study.study_instance_uid
        link = auth_client.patch(f'/api/dicom/studies/{uid}',
                                 {'animal_patient_id': animal['id']}, format='json')
        assert link.status_code == 200, link.content
        assert link.data['animal_patient_id'] == animal['id']

        # Patient detail now shows the study in its timeline
        detail = auth_client.get(f"/api/patients/animals/{animal['id']}/")
        uids = [s['study_instance_uid'] for s in detail.data['studies']]
        assert uid in uids

        # Unlink
        unlink = auth_client.patch(f'/api/dicom/studies/{uid}',
                                   {'animal_patient_id': None}, format='json')
        assert unlink.status_code == 200
        assert unlink.data['animal_patient_id'] is None
