"""
Tests for owner↔clinic messaging (#22): the shared per-animal thread, scoping
for staff vs owner accounts, mark-read, and counterpart notifications.
"""
import pytest
from rest_framework.test import APIClient

from users.models import User, PET_OWNER_ROLE


@pytest.fixture
def owner_account(owner):
    return User.objects.create_user(email=owner.email, password='OwnerPass123!', role=PET_OWNER_ROLE)


@pytest.fixture
def owner_client(owner_account):
    client = APIClient()
    client.force_authenticate(user=owner_account)
    return client


def _make_in_org_animal(auth_client):
    o = auth_client.post('/api/patients/owners/', {
        'first_name': 'Msg', 'last_name': 'Owner',
        'email': 'msgowner@example.com', 'phone': '555-0300',
    }, format='json').data
    return auth_client.post('/api/patients/animals/', {
        'owner_id': o['id'], 'name': 'Buddy', 'species': 'canine',
    }, format='json').data


@pytest.mark.django_db
class TestMessagingStaff:
    BASE = '/api/patients/messages/'

    def test_staff_posts_message_marked_from_clinic(self, auth_client):
        animal = _make_in_org_animal(auth_client)
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal['id'], 'body': 'Please bring Buddy in Monday.',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['from_owner'] is False
        assert resp.data['body'] == 'Please bring Buddy in Monday.'

    def test_empty_body_rejected(self, auth_client):
        animal = _make_in_org_animal(auth_client)
        resp = auth_client.post(self.BASE, {'animal_patient_id': animal['id'], 'body': '   '}, format='json')
        assert resp.status_code == 400

    def test_thread_filtered_by_animal(self, auth_client):
        animal = _make_in_org_animal(auth_client)
        auth_client.post(self.BASE, {'animal_patient_id': animal['id'], 'body': 'Hi'}, format='json')
        resp = auth_client.get(f"{self.BASE}?animal={animal['id']}")
        rows = resp.data.get('results') if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        assert len(rows) == 1

    def test_cross_org_animal_denied(self, auth_client, animal_patient):
        resp = auth_client.post(self.BASE, {
            'animal_patient_id': animal_patient.id, 'body': 'x',
        }, format='json')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestMessagingOwnerAndNotifications:
    BASE = '/api/patients/messages/'

    def test_owner_sees_and_replies_to_thread(self, auth_client, owner_client, animal_patient):
        # Clinic (different fixture org) won't match; use the owner's own animal.
        # animal_patient belongs to `owner` fixture whose email == owner_account email.
        # Owner posts a message:
        resp = owner_client.post(self.BASE, {
            'animal_patient_id': animal_patient.id, 'body': 'Is Rex ok to eat before the scan?',
        }, format='json')
        assert resp.status_code == 201, resp.content
        assert resp.data['from_owner'] is True

        listed = owner_client.get(f"{self.BASE}?animal={animal_patient.id}")
        rows = listed.data.get('results') if isinstance(listed.data, dict) and 'results' in listed.data else listed.data
        assert any(m['body'].startswith('Is Rex') for m in rows)

    def test_owner_cannot_see_other_animals(self, owner_client, animal_patient, organization):
        from patients.models import Owner, AnimalPatient, Message
        other = Owner.objects.create(
            organization=organization, first_name='X', last_name='Y',
            email='someone.else@example.com', phone='555-0400',
        )
        other_animal = AnimalPatient.objects.create(owner=other, name='Stranger', species='feline')
        Message.objects.create(animal_patient=other_animal, body='secret', from_owner=False)
        resp = owner_client.get(self.BASE)
        rows = resp.data.get('results') if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        assert all(m.get('body') != 'secret' for m in rows)

    def test_owner_message_notifies_clinic(self, owner_client, animal_patient, organization):
        from credentials.models import Notification
        owner_client.post(self.BASE, {
            'animal_patient_id': animal_patient.id, 'body': 'Quick question',
        }, format='json')
        # organization.user is the clinic staff account that should be notified.
        assert Notification.objects.filter(user=organization.user).exists()

    def test_mark_read_marks_other_side(self, auth_client, owner_client, animal_patient):
        # Owner sends one; staff marks it read.
        owner_client.post(self.BASE, {'animal_patient_id': animal_patient.id, 'body': 'hello'}, format='json')
        # auth_client is a different org, so it can't see animal_patient. Use the
        # owner marking the clinic's message instead: clinic message first.
        from patients.models import Message
        Message.objects.create(animal_patient=animal_patient, body='from clinic', from_owner=False)
        resp = owner_client.post(f"{self.BASE}mark_read/", {'animal': animal_patient.id}, format='json')
        assert resp.status_code == 200
        assert resp.data['marked_read'] == 1  # only the clinic message
        assert Message.objects.get(body='from clinic').is_read is True
