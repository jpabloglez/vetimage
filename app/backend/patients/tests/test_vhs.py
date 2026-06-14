"""
Tests for the Vertebral Heart Score (VHS) measurement feature.
"""
import pytest


@pytest.mark.django_db
class TestVHS:
    def _owner_and_animal(self, auth_client, species='canine'):
        owner = auth_client.post('/api/patients/owners/', {
            'first_name': 'V', 'last_name': 'Owner',
        }, format='json').data
        animal = auth_client.post('/api/patients/animals/', {
            'owner_id': owner['id'], 'name': 'Cardio', 'species': species,
        }, format='json').data
        return animal

    def test_vhs_computed_server_side(self, auth_client):
        animal = self._owner_and_animal(auth_client, 'canine')
        resp = auth_client.post('/api/patients/vhs/', {
            'animal_patient_id': animal['id'],
            'measured_on': '2026-01-15',
            'long_axis_vertebrae': '5.5',
            'short_axis_vertebrae': '4.5',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert str(resp.data['vhs']) == '10.0'  # 5.5 + 4.5
        assert resp.data['interpretation'] == 'within_range'  # canine 8.5–10.6
        assert resp.data['reference_range'] == {'low': 8.5, 'high': 10.6}

    def test_vhs_above_range_flagged(self, auth_client):
        animal = self._owner_and_animal(auth_client, 'canine')
        resp = auth_client.post('/api/patients/vhs/', {
            'animal_patient_id': animal['id'],
            'measured_on': '2026-02-01',
            'long_axis_vertebrae': '6.5',
            'short_axis_vertebrae': '5.5',
        }, format='json')
        assert resp.status_code == 201
        assert str(resp.data['vhs']) == '12.0'
        assert resp.data['interpretation'] == 'above_range'

    def test_vhs_trend_in_animal_detail(self, auth_client):
        animal = self._owner_and_animal(auth_client, 'feline')
        for d, l, s in [('2026-01-01', '3.5', '3.5'), ('2026-03-01', '4.0', '4.5')]:
            auth_client.post('/api/patients/vhs/', {
                'animal_patient_id': animal['id'], 'measured_on': d,
                'long_axis_vertebrae': l, 'short_axis_vertebrae': s,
            }, format='json')
        detail = auth_client.get(f"/api/patients/animals/{animal['id']}/")
        trend = detail.data['vhs_trend']
        assert len(trend) == 2
        # chronological order, values computed
        assert trend[0]['measured_on'] == '2026-01-01' and trend[0]['vhs'] == 7.0
        assert trend[1]['vhs'] == 8.5

    def test_vhs_list_filtered_by_animal(self, auth_client):
        a1 = self._owner_and_animal(auth_client, 'canine')
        a2 = self._owner_and_animal(auth_client, 'canine')
        auth_client.post('/api/patients/vhs/', {
            'animal_patient_id': a1['id'], 'measured_on': '2026-01-01',
            'long_axis_vertebrae': '5.0', 'short_axis_vertebrae': '5.0',
        }, format='json')
        resp = auth_client.get(f"/api/patients/vhs/?animal={a2['id']}")
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        assert results == []
