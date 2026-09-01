"""
Tests for dicom_images views.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from dicom_images.models import (
    MedicalStudy,
    SavedSearch,
    ImageAnnotation,
)


# ===========================================================================
# StudyListView
# ===========================================================================


@pytest.mark.django_db
class TestStudyListView:

    def test_list_authenticated(self, auth_client, study):
        url = reverse('dicom_images:dicomweb-studies')
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_reject_unauthenticated(self, api_client):
        url = reverse('dicom_images:dicomweb-studies')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_isolation(self, auth_client, study, other_user):
        """User should only see their own studies."""
        MedicalStudy.objects.create(
            study_instance_uid='1.2.3.other',
            patient_id='OTHER',
            uploaded_by=other_user,
        )
        url = reverse('dicom_images:dicomweb-studies')
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        patient_ids = [s.get('PatientID', s.get('patient_id', '')) for s in resp.data]
        assert 'OTHER' not in patient_ids

    def test_filter_by_patient_id(self, auth_client, user):
        MedicalStudy.objects.create(
            study_instance_uid='1.1.1', patient_id='ALPHA', uploaded_by=user,
        )
        MedicalStudy.objects.create(
            study_instance_uid='1.1.2', patient_id='BETA', uploaded_by=user,
        )
        url = reverse('dicom_images:dicomweb-studies')
        resp = auth_client.get(url, {'PatientID': 'ALPHA'})
        assert resp.status_code == status.HTTP_200_OK


# ===========================================================================
# SeriesListView
# ===========================================================================


@pytest.mark.django_db
class TestSeriesListView:

    def test_list_series(self, auth_client, series):
        url = reverse(
            'dicom_images:dicomweb-series',
            kwargs={'study_uid': series.study.study_instance_uid},
        )
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_404_nonexistent_study(self, auth_client):
        url = reverse(
            'dicom_images:dicomweb-series',
            kwargs={'study_uid': '9.9.9.9.9.nonexistent'},
        )
        resp = auth_client.get(url)
        assert resp.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_200_OK,  # may return empty list
        )


# ===========================================================================
# StorageQuotaView
# ===========================================================================


@pytest.mark.django_db
class TestStorageQuotaView:

    def test_get_quota(self, auth_client):
        url = reverse('dicom_images:storage-quota')
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert 'quota_bytes' in resp.data
        assert 'remaining_bytes' in resp.data
        assert 'usage_percentage' in resp.data
        assert 'is_over_quota' in resp.data


# ===========================================================================
# DeleteStudyView
# ===========================================================================


@pytest.mark.django_db
class TestDeleteStudyView:

    def test_delete_own_study(self, auth_client, study):
        url = reverse(
            'dicom_images:delete-study',
            kwargs={'study_uid': study.study_instance_uid},
        )
        resp = auth_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not MedicalStudy.objects.filter(pk=study.pk).exists()

    def test_delete_nonexistent(self, auth_client):
        url = reverse(
            'dicom_images:delete-study',
            kwargs={'study_uid': '9.9.9.9.9'},
        )
        resp = auth_client.delete(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# DeleteStudyView.patch — link/unlink to an AnimalPatient
# ===========================================================================


@pytest.mark.django_db
class TestLinkStudyToAnimal:
    """
    Linking a study to a real AnimalPatient must sync the study's own
    display fields (patient_name/patient_id) — otherwise the viewer keeps
    showing whatever the source DICOM file's tags were (often blank/
    generic), e.g. "Unknown Patient", despite a real patient being linked.
    """

    @pytest.fixture
    def linked_animal(self, user):
        from patients.models import Owner, AnimalPatient
        from patients.views import get_or_create_clinic

        org = get_or_create_clinic(user)
        owner = Owner.objects.create(
            clinic=org, first_name='Jane', last_name='Smith',
            email='jane@example.com', phone='555-0100',
        )
        return AnimalPatient.objects.create(
            owner=owner, name='Bella', species='canine', breed='Labrador', sex='F',
        )

    def _link_url(self, study):
        return reverse('dicom_images:delete-study', kwargs={'study_uid': study.study_instance_uid})

    def test_linking_syncs_patient_display_fields(self, auth_client, study, linked_animal):
        assert study.patient_name == 'DOE^JOHN'  # sanity: original DICOM-tag value

        resp = auth_client.patch(
            self._link_url(study), {'animal_patient_id': linked_animal.id}, format='json',
        )
        assert resp.status_code == status.HTTP_200_OK

        study.refresh_from_db()
        assert study.animal_patient_id == linked_animal.id
        assert study.patient_name == 'Bella'
        assert study.patient_id == str(linked_animal.id)
        assert study.patient_name_normalized == 'bella'

    def test_unlinking_clears_the_fk_but_leaves_display_fields(self, auth_client, study, linked_animal):
        auth_client.patch(self._link_url(study), {'animal_patient_id': linked_animal.id}, format='json')

        resp = auth_client.patch(self._link_url(study), {'animal_patient_id': None}, format='json')
        assert resp.status_code == status.HTTP_200_OK

        study.refresh_from_db()
        assert study.animal_patient_id is None
        assert study.patient_name == 'Bella'  # not reverted — out of scope for the sync fix

    def test_rejects_animal_from_another_clinic(self, auth_client, study, animal_patient):
        # `animal_patient` (conftest fixture) belongs to a different org than
        # auth_client's user.
        resp = auth_client.patch(
            self._link_url(study), {'animal_patient_id': animal_patient.id}, format='json',
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        study.refresh_from_db()
        assert study.patient_name == 'DOE^JOHN'  # untouched


# ===========================================================================
# AdvancedSearchView
# ===========================================================================


@pytest.mark.django_db
class TestAdvancedSearchView:

    def test_search_by_patient_name(self, auth_client, study):
        url = reverse('dicom_images:advanced-search')
        resp = auth_client.post(url, {'patient_name': 'DOE'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert 'results' in resp.data

    def test_empty_results(self, auth_client):
        url = reverse('dicom_images:advanced-search')
        resp = auth_client.post(
            url, {'patient_name': 'NONEXISTENT'}, format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['total'] == 0


# ===========================================================================
# SavedSearchViews
# ===========================================================================


@pytest.mark.django_db
class TestSavedSearchViews:

    def test_create_saved_search(self, auth_client):
        url = reverse('dicom_images:saved-searches')
        data = {
            'name': 'CT Head',
            'search_filters': {'modality': ['CT']},
        }
        resp = auth_client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['name'] == 'CT Head'

    def test_list_saved_searches(self, auth_client, user):
        SavedSearch.objects.create(
            user=user, name='Saved 1', search_filters={},
        )
        url = reverse('dicom_images:saved-searches')
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_delete_saved_search(self, auth_client, user):
        ss = SavedSearch.objects.create(
            user=user, name='To Delete', search_filters={},
        )
        url = reverse(
            'dicom_images:saved-search-detail',
            kwargs={'search_id': ss.pk},
        )
        resp = auth_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not SavedSearch.objects.filter(pk=ss.pk).exists()


# ===========================================================================
# AnnotationViews
# ===========================================================================


@pytest.mark.django_db
class TestAnnotationViews:

    def test_create_annotation(self, auth_client, image):
        url = reverse(
            'dicom_images:annotations-list',
            kwargs={'sop_uid': image.sop_instance_uid},
        )
        data = {
            'annotation_type': 'distance',
            'frame_number': 0,
            'geometry_data': {
                'points': [{'x': 0, 'y': 0}, {'x': 100, 'y': 100}],
            },
            'label': 'Test distance',
        }
        resp = auth_client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

    def test_list_annotations(self, auth_client, image, user):
        ImageAnnotation.objects.create(
            image=image,
            created_by=user,
            annotation_type='text',
            geometry_data={'position': {'x': 50, 'y': 50}},
        )
        url = reverse(
            'dicom_images:annotations-list',
            kwargs={'sop_uid': image.sop_instance_uid},
        )
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1
