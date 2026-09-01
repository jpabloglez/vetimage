"""
Query-count and parameter-handling guarantees for the DICOMweb list endpoints.

The study list is the app's most-used screen. Its serializer exposes
number_of_series / number_of_instances, which are model properties that each
run their own COUNT — so before the annotation was added, one page of 100
studies cost roughly 201 queries. The assertions here are deliberately
count-based: a regression re-introduces the N+1 silently, with correct output
and no failing behavioural test.
"""

import pytest
from django.urls import reverse

from dicom_images.models import MedicalStudy, MedicalSeries, MedicalImage
from dicom_images.serializers import DICOMwebStudySerializer


def _make_study(user, n, series_per_study=2, images_per_series=3):
    """Build *n* studies with a realistic fan-out."""
    for s in range(n):
        study = MedicalStudy.objects.create(
            study_instance_uid=f'1.2.900.{s}', patient_id=f'P{s}',
            patient_name=f'Patient {s}', uploaded_by=user,
        )
        for si in range(series_per_study):
            series = MedicalSeries.objects.create(
                study=study, series_instance_uid=f'1.2.900.{s}.{si}',
                series_number=si, modality='CR',
            )
            for ii in range(images_per_series):
                MedicalImage.objects.create(
                    series=series, sop_instance_uid=f'1.2.900.{s}.{si}.{ii}',
                    sop_class_uid='1.2.840.10008.5.1.4.1.1.1.1',
                    instance_number=ii, original_filename='x.dcm', file_size_bytes=1,
                )


@pytest.mark.django_db
class TestStudyListQueryCount:

    def test_endpoint_query_count_does_not_grow_with_row_count(self, auth_client, user):
        """
        The guarantee that matters: hitting the real endpoint with 1 study and
        with 8 studies must issue the same number of queries. Without the
        annotation this grows by 2 per row (~201 at the default limit=100).

        Asserted as a delta rather than an absolute, so unrelated middleware or
        auth queries don't make this brittle.
        """
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        url = reverse('dicom_images:dicomweb-studies')

        _make_study(user, 1)
        # Warm-up: org scoping calls get_or_create_organization, which lazily
        # provisions a UserProfile + Organization on first use. That one-off
        # cost is not what this test is guarding, so pay it before measuring.
        auth_client.get(url)

        with CaptureQueriesContext(connection) as few:
            assert auth_client.get(url).status_code == 200

        _make_study(user, 7)  # 8 total
        with CaptureQueriesContext(connection) as many:
            resp = auth_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 8

        assert len(many) == len(few), (
            f'query count scaled with rows: {len(few)} for 1 study vs '
            f'{len(many)} for 8 — the N+1 is back'
        )

    def test_serializer_needs_only_one_query_when_annotated(self, user, django_assert_num_queries):
        _make_study(user, 8)
        with django_assert_num_queries(1):
            data = DICOMwebStudySerializer(_annotated(user), many=True).data
        assert len(data) == 8

    def test_annotated_counts_are_correct_with_fan_out(self, auth_client, user):
        """
        Two COUNTs over a multi-valued join will multiply each other unless
        both are distinct. 2 series x 3 images must read as 2 and 6, not 6 and 6.
        """
        _make_study(user, 1, series_per_study=2, images_per_series=3)
        resp = auth_client.get(reverse('dicom_images:dicomweb-studies'))
        assert resp.status_code == 200
        row = resp.data[0]
        assert row['NumberOfStudyRelatedSeries'] == 2
        assert row['NumberOfStudyRelatedInstances'] == 6

    def test_properties_still_work_without_an_annotation(self, study, series, image):
        """Un-annotated access (admin, single-object views) must keep working."""
        fresh = MedicalStudy.objects.get(pk=study.pk)
        assert fresh.number_of_series == 1
        assert fresh.number_of_instances == 1


def _annotated(user):
    from django.db import models as m
    return (
        MedicalStudy.objects.filter(uploaded_by=user)
        .select_related('animal_patient')
        .annotate(
            _series_count=m.Count('series', distinct=True),
            _instance_count=m.Count('series__images', distinct=True),
        )
    )


@pytest.mark.django_db
class TestListParameterHandling:
    """`int(request.query_params.get(...))` used to 500 on junk input."""

    def _url(self):
        return reverse('dicom_images:dicomweb-studies')

    @pytest.mark.parametrize('bad', ['abc', '', '1.5', 'null', '--1'])
    def test_non_numeric_limit_falls_back_instead_of_500(self, auth_client, user, bad):
        _make_study(user, 2)
        resp = auth_client.get(self._url(), {'limit': bad})
        assert resp.status_code == 200, f'limit={bad!r} should not error'

    def test_oversized_limit_is_clamped(self, auth_client, user):
        from core.query_params import MAX_PAGE_SIZE
        _make_study(user, 3)
        resp = auth_client.get(self._url(), {'limit': '99999999'})
        assert resp.status_code == 200
        assert len(resp.data) <= MAX_PAGE_SIZE

    def test_negative_offset_does_not_error(self, auth_client, user):
        _make_study(user, 2)
        resp = auth_client.get(self._url(), {'offset': '-5'})
        assert resp.status_code == 200

    def test_limit_is_still_honoured(self, auth_client, user):
        _make_study(user, 5)
        resp = auth_client.get(self._url(), {'limit': '2'})
        assert resp.status_code == 200
        assert len(resp.data) == 2
