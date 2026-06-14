"""
Tests for HL7 ORU^R01 and FHIR DiagnosticReport lab imports.
"""
import pytest


SAMPLE_HL7_ORU = (
    'MSH|^~\\&|IDEXX|VetLabStation|VetImage|Clinic|20260210120000||ORU^R01|MSG0001|P|2.5\r'
    'PID|1||PAT001||Rex^^||20200101|M\r'
    'OBR|1||ACC123|CBC^Complete Blood Count^L|||20260210113000\r'
    'OBX|1|NM|WBC^White Blood Cells||12.5|10*3/uL^10^3/uL|5.5-16.9|N|||F\r'
    'OBX|2|NM|RBC^Red Blood Cells||4.2|10*6/uL^10^6/uL|5.5-8.5|L|||F\r'
    'OBX|3|NM|HGB^Hemoglobin||18.2|g/dL^g/dL|12.0-18.0|H|||F\r'
)

SAMPLE_FHIR_REPORT = {
    'resourceType': 'DiagnosticReport',
    'status': 'final',
    'code': {'text': 'Chemistry Panel'},
    'effectiveDateTime': '2026-02-11T09:30:00Z',
    'performer': [{'display': 'Heska Element DC'}],
    'contained': [
        {
            'resourceType': 'Observation',
            'code': {'text': 'Creatinine'},
            'valueQuantity': {'value': 1.4, 'unit': 'mg/dL'},
            'referenceRange': [{'low': {'value': 0.5}, 'high': {'value': 1.8}}],
            'interpretation': [{'coding': [{'code': 'N'}]}],
        },
        {
            'resourceType': 'Observation',
            'code': {'text': 'BUN'},
            'valueQuantity': {'value': 42.0, 'unit': 'mg/dL'},
            'referenceRange': [{'low': {'value': 7.0}, 'high': {'value': 27.0}}],
            'interpretation': [{'coding': [{'code': 'H'}]}],
        },
    ],
}


@pytest.mark.django_db
class TestHL7Import:
    BASE = '/api/patients/labs/import-hl7/'

    def _make_animal(self, auth_client):
        o = auth_client.post('/api/patients/owners/', {
            'first_name': 'Hl', 'last_name': 'Seven',
            'email': 'hl7@example.com', 'phone': '555-0040',
        }, format='json').data
        return auth_client.post('/api/patients/animals/', {
            'owner_id': o['id'], 'name': 'Toby', 'species': 'canine',
        }, format='json').data

    def test_import_oru_creates_lab_result(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'message': SAMPLE_HL7_ORU,
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['panel_name'] == 'Complete Blood Count'
        assert resp.data['result_type'] == 'hematology'  # inferred from "Blood Count"
        assert resp.data['result_date'] == '2026-02-10'
        data = resp.data['result_data']
        assert data['White Blood Cells']['value'] == 12.5
        assert data['Red Blood Cells']['flag'] == 'L'
        assert data['Hemoglobin']['ref_high'] == 18.0
        assert resp.data['lab_name'] == 'VetLabStation'

    def test_import_invalid_hl7_400(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'message': 'this is not HL7',
        }, format='json')
        assert resp.status_code == 400

    def test_import_missing_animal_400(self, auth_client):
        resp = auth_client.post(self.BASE, {'message': SAMPLE_HL7_ORU}, format='json')
        assert resp.status_code == 400

    def test_import_cross_org_denied(self, auth_client, animal_patient):
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal_patient.id,  # other org
            'message': SAMPLE_HL7_ORU,
        }, format='json')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestFHIRImport:
    BASE = '/api/patients/labs/import-fhir/'

    def _make_animal(self, auth_client):
        o = auth_client.post('/api/patients/owners/', {
            'first_name': 'Fh', 'last_name': 'Ir',
            'email': 'fhir@example.com', 'phone': '555-0041',
        }, format='json').data
        return auth_client.post('/api/patients/animals/', {
            'owner_id': o['id'], 'name': 'Mia', 'species': 'feline',
        }, format='json').data

    def test_import_diagnostic_report(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'report': SAMPLE_FHIR_REPORT,
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['panel_name'] == 'Chemistry Panel'
        assert resp.data['result_type'] == 'biochemistry'
        assert resp.data['result_date'] == '2026-02-11'
        assert resp.data['lab_name'] == 'Heska Element DC'
        data = resp.data['result_data']
        assert data['BUN']['flag'] == 'H'
        assert data['Creatinine']['ref_low'] == 0.5

    def test_import_wrong_resource_type_400(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'report': {'resourceType': 'Patient'},
        }, format='json')
        assert resp.status_code == 400

    def test_import_no_observations_400(self, auth_client):
        animal = self._make_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'],
            'report': {'resourceType': 'DiagnosticReport', 'code': {'text': 'X'}, 'contained': []},
        }, format='json')
        assert resp.status_code == 400
