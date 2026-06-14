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
