"""
Tests for dicom_images models.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from dicom_images.models import (
    MedicalStudy,
    MedicalSeries,
    MedicalImage,
    UserStorageQuota,
    SavedSearch,
    ImageAnnotation,
    AnnotationTemplate,
)

User = get_user_model()


# ===========================================================================
# MedicalStudy
# ===========================================================================


@pytest.mark.django_db
class TestMedicalStudy:

    def test_creation(self, study):
        assert study.pk is not None
        assert study.patient_id == 'PAT001'
        assert study.patient_name == 'DOE^JOHN'

    def test_str_repr(self, study):
        s = str(study)
        assert 'Study' in s
        assert 'DOE^JOHN' in s

    def test_str_repr_without_patient_name(self, user):
        study = MedicalStudy.objects.create(
            study_instance_uid='1.2.3.4.5',
            patient_id='PAT002',
            patient_name='',
            uploaded_by=user,
        )
        assert 'PAT002' in str(study)

    def test_number_of_series(self, study, series):
        assert study.number_of_series == 1

    def test_number_of_instances(self, study, series, image):
        assert study.number_of_instances == 1

    def test_ordering(self, user):
        s1 = MedicalStudy.objects.create(
            study_instance_uid='1.1.1', patient_id='P1', uploaded_by=user,
        )
        s2 = MedicalStudy.objects.create(
            study_instance_uid='1.1.2', patient_id='P2', uploaded_by=user,
        )
        studies = list(MedicalStudy.objects.filter(uploaded_by=user))
        # Ordering is -uploaded_at, so most recent first
        assert studies[0].pk == s2.pk


# ===========================================================================
# MedicalSeries
# ===========================================================================


@pytest.mark.django_db
class TestMedicalSeries:

    def test_creation(self, series):
        assert series.pk is not None
        assert series.modality == 'CT'

    def test_number_of_instances(self, series, image):
        assert series.number_of_instances == 1

    def test_str_repr(self, series):
        s = str(series)
        assert 'CT' in s
        assert 'Series' in s


# ===========================================================================
# MedicalImage
# ===========================================================================


@pytest.mark.django_db
class TestMedicalImage:

    def test_creation(self, image):
        assert image.pk is not None
        assert image.original_filename == 'test.dcm'

    def test_file_size_tracking(self, series):
        """file_size_bytes is set from file.size on save when not provided."""
        dummy = SimpleUploadedFile('auto.dcm', b'\x00' * 100)
        img = MedicalImage.objects.create(
            series=series,
            sop_instance_uid='1.2.3.auto',
            sop_class_uid='1.2.840.10008.5.1.4.1.1.2',
            instance_number=2,
            file=dummy,
            original_filename='auto.dcm',
            # file_size_bytes intentionally left as default 0
        )
        # After save the model should have auto-populated from file.size
        assert img.file_size_bytes > 0

    def test_str_repr(self, image):
        s = str(image)
        assert 'Instance' in s
        assert 'test.dcm' in s


# ===========================================================================
# UserStorageQuota
# ===========================================================================


@pytest.mark.django_db
class TestUserStorageQuota:

    def test_remaining_bytes(self, user):
        quota = UserStorageQuota.objects.create(
            user=user, used_bytes=1000, quota_bytes=5000,
        )
        assert quota.remaining_bytes == 4000

    def test_usage_percentage(self, user):
        quota = UserStorageQuota.objects.create(
            user=user, used_bytes=2500, quota_bytes=5000,
        )
        assert quota.usage_percentage == pytest.approx(50.0)

    def test_is_over_quota_false(self, user):
        quota = UserStorageQuota.objects.create(
            user=user, used_bytes=1000, quota_bytes=5000,
        )
        assert quota.is_over_quota is False

    def test_is_over_quota_true(self, user):
        quota = UserStorageQuota.objects.create(
            user=user, used_bytes=5000, quota_bytes=5000,
        )
        assert quota.is_over_quota is True

    def test_zero_quota_usage_percentage(self, user):
        quota = UserStorageQuota.objects.create(
            user=user, used_bytes=0, quota_bytes=0,
        )
        assert quota.usage_percentage == 100

    def test_over_quota_remaining_bytes(self, user):
        quota = UserStorageQuota.objects.create(
            user=user, used_bytes=6000, quota_bytes=5000,
        )
        assert quota.remaining_bytes == 0

    def test_update_usage(self, user, study):
        quota = UserStorageQuota.objects.create(
            user=user, used_bytes=0, quota_bytes=5000,
        )
        result = quota.update_usage()
        assert result == study.total_size_bytes

    def test_str_repr(self, user):
        quota = UserStorageQuota.objects.create(
            user=user, used_bytes=100, quota_bytes=5000,
        )
        assert user.email in str(quota)


# ===========================================================================
# SavedSearch
# ===========================================================================


@pytest.mark.django_db
class TestSavedSearch:

    def test_creation(self, user):
        ss = SavedSearch.objects.create(
            user=user,
            name='CT Head Scans',
            search_filters={'modality': ['CT'], 'body_part': 'HEAD'},
        )
        assert ss.pk is not None

    def test_use_count_default(self, user):
        ss = SavedSearch.objects.create(
            user=user, name='Test', search_filters={},
        )
        assert ss.use_count == 0

    def test_str_repr(self, user):
        ss = SavedSearch.objects.create(
            user=user, name='My Search', search_filters={},
        )
        assert 'My Search' in str(ss)
        assert user.email in str(ss)


# ===========================================================================
# ImageAnnotation
# ===========================================================================


@pytest.mark.django_db
class TestImageAnnotation:

    def test_creation(self, image, user):
        ann = ImageAnnotation.objects.create(
            image=image,
            created_by=user,
            annotation_type='distance',
            geometry_data={'points': [{'x': 0, 'y': 0}, {'x': 10, 'y': 10}]},
            label='Test measurement',
        )
        assert ann.pk is not None

    def test_default_visibility(self, image, user):
        ann = ImageAnnotation.objects.create(
            image=image,
            created_by=user,
            annotation_type='text',
            geometry_data={'position': {'x': 50, 'y': 50}, 'text': 'Finding'},
        )
        assert ann.visibility == 'private'

    def test_str_repr(self, image, user):
        ann = ImageAnnotation.objects.create(
            image=image,
            created_by=user,
            annotation_type='roi',
            geometry_data={'points': []},
        )
        assert 'roi' in str(ann)
        assert user.email in str(ann)


# ===========================================================================
# AnnotationTemplate
# ===========================================================================


@pytest.mark.django_db
class TestAnnotationTemplate:

    def test_creation(self, user):
        tmpl = AnnotationTemplate.objects.create(
            user=user,
            name='Lung Nodule ROI',
            annotation_type='roi',
            default_properties={'color': '#FF0000', 'lineWidth': 2},
        )
        assert tmpl.pk is not None

    def test_str_repr(self, user):
        tmpl = AnnotationTemplate.objects.create(
            user=user,
            name='Brain Lesion',
            annotation_type='ellipse',
            default_properties={'color': '#00FF00'},
        )
        assert 'Brain Lesion' in str(tmpl)
        assert 'ellipse' in str(tmpl)
