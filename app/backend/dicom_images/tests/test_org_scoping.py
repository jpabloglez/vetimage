"""
Studies are clinic-scoped, like the rest of the clinical record.

Two directions matter equally here, and a mistake in either is serious:
colleagues in the same clinic must gain access, and users in a
*different* clinic must not. The previous rule was `uploaded_by=user`.
"""

import pytest
from django.urls import reverse

from dicom_images.models import MedicalStudy
from dicom_images.scoping import visible_studies


def _user(email, org=None):
    from django.contrib.auth import get_user_model
    from users.models import UserProfile
    U = get_user_model()
    u = U.objects.create_user(email=email, password='TestPass123!', role=1)
    profile, _ = UserProfile.objects.get_or_create(user=u)
    if org is not None:
        profile.clinic = org
        profile.save(update_fields=['clinic'])
    return u


def _study(user, uid):
    return MedicalStudy.objects.create(
        study_instance_uid=uid, patient_id='P', patient_name='Rex', uploaded_by=user,
    )


@pytest.fixture
def clinic():
    from users.models import Clinic
    from django.contrib.auth import get_user_model
    U = get_user_model()
    owner = U.objects.create_user(email='clinic-owner@x.test', password='x', role=1)
    return Clinic.objects.create(
        user=owner, name='Clinic A', address='', city='',
        billing_address='', billing_code='',
    )


@pytest.fixture
def other_clinic():
    from users.models import Clinic
    from django.contrib.auth import get_user_model
    U = get_user_model()
    owner = U.objects.create_user(email='other-owner@x.test', password='x', role=1)
    return Clinic.objects.create(
        user=owner, name='Clinic B', address='', city='',
        billing_address='', billing_code='',
    )


@pytest.mark.django_db
class TestStudyOrgScoping:

    def test_colleague_can_see_my_study(self, clinic):
        vet_a = _user('vet-a@x.test', clinic)
        vet_b = _user('vet-b@x.test', clinic)
        _study(vet_a, '1.2.3.A')

        assert visible_studies(vet_b).filter(study_instance_uid='1.2.3.A').exists(), (
            'a colleague in the same clinic must see the study'
        )

    def test_other_clinic_cannot_see_it(self, clinic, other_clinic):
        vet_a = _user('vet-a2@x.test', clinic)
        outsider = _user('outsider@x.test', other_clinic)
        _study(vet_a, '1.2.3.B')

        assert not visible_studies(outsider).filter(study_instance_uid='1.2.3.B').exists(), (
            'a user in a different clinic must NOT see the study'
        )

    def test_uploader_keeps_access_without_an_clinic(self):
        """
        The rule is `own OR same-org`, not just `same-org`. A user whose profile
        has no clinic would otherwise drop out of the join and lose access
        to their own studies — a regression the org filter alone would cause.
        """
        loner = _user('loner@x.test', org=None)
        _study(loner, '1.2.3.C')

        assert visible_studies(loner).filter(study_instance_uid='1.2.3.C').exists()

    def test_applies_to_pre_existing_studies(self, clinic):
        """Scoping is computed at query time, so historical rows are included."""
        vet_a = _user('vet-a3@x.test', clinic)
        _study(vet_a, '1.2.3.D')          # "already in the database"
        vet_b = _user('vet-b3@x.test', clinic)  # joins the clinic afterwards

        assert visible_studies(vet_b).filter(study_instance_uid='1.2.3.D').exists()


@pytest.mark.django_db
class TestStudyOrgScopingThroughTheAPI:

    def _login(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    def test_study_list_includes_colleague_studies(self, api_client, clinic):
        vet_a = _user('api-a@x.test', clinic)
        vet_b = _user('api-b@x.test', clinic)
        _study(vet_a, '1.2.9.A')

        resp = self._login(api_client, vet_b).get(reverse('dicom_images:dicomweb-studies'))
        assert resp.status_code == 200
        assert [r['StudyInstanceUID'] for r in resp.data] == ['1.2.9.A']

    def test_study_list_excludes_other_org_studies(self, api_client, clinic, other_clinic):
        vet_a = _user('api-a2@x.test', clinic)
        outsider = _user('api-out@x.test', other_clinic)
        _study(vet_a, '1.2.9.B')

        resp = self._login(api_client, outsider).get(reverse('dicom_images:dicomweb-studies'))
        assert resp.status_code == 200
        assert resp.data == []

    def test_colleague_can_read_study_tags(self, api_client, clinic):
        """A representative non-list endpoint — proves scoping reached the
        services/serializers too, not just the study list."""
        vet_a = _user('api-a4@x.test', clinic)
        vet_b = _user('api-b4@x.test', clinic)
        _study(vet_a, '1.2.9.D')

        resp = self._login(api_client, vet_b).get('/api/dicom/studies/1.2.9.D/tags/')
        assert resp.status_code == 200
        assert resp.data['patient_name'] == 'Rex'

    def test_outsider_cannot_read_study_tags(self, api_client, clinic, other_clinic):
        vet_a = _user('api-a5@x.test', clinic)
        outsider = _user('api-out5@x.test', other_clinic)
        _study(vet_a, '1.2.9.E')

        resp = self._login(api_client, outsider).get('/api/dicom/studies/1.2.9.E/tags/')
        assert resp.status_code == 404

    def test_duplicate_uid_across_colleagues_does_not_500(self, api_client, clinic):
        """
        Org scoping makes it possible for two colleagues to hold the same
        StudyInstanceUID. Endpoints that used .get() would raise
        MultipleObjectsReturned; they must return the newest instead.
        """
        vet_a = _user('dup-a@x.test', clinic)
        vet_b = _user('dup-b@x.test', clinic)
        _study(vet_a, '1.2.9.DUP')
        _study(vet_b, '1.2.9.DUP')

        resp = self._login(api_client, vet_b).get('/api/dicom/studies/1.2.9.DUP/tags/')
        assert resp.status_code == 200
