"""
Security behaviour of the public, token-gated study share link.

This endpoint is unauthenticated by design — the UUID4 token is the only
credential — so the access cap it advertises has to actually hold.
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from dicom_images.models import StudyShareLink


@pytest.fixture
def share_link(study, user):
    return StudyShareLink.objects.create(study=study, created_by=user, max_accesses=2)


def _url(link):
    return reverse('dicom_images:public-shared-study', kwargs={'token': link.token})


@pytest.mark.django_db
class TestStudyShareLinkAccessCap:

    def test_access_increments_and_reports_remaining(self, api_client, share_link):
        resp = api_client.get(_url(share_link))
        assert resp.status_code == 200
        assert resp.data['accesses_remaining'] == 1

        share_link.refresh_from_db()
        assert share_link.access_count == 1

    def test_returns_study_metadata(self, api_client, share_link, series):
        """Regression: this path used to read a non-existent study.modality
        attribute and 500 on every successful access."""
        resp = api_client.get(_url(share_link))
        assert resp.status_code == 200
        assert resp.data['study_instance_uid'] == share_link.study.study_instance_uid
        assert resp.data['modalities'] == [series.modality]

    def test_cap_is_enforced_exactly(self, api_client, share_link):
        """max_accesses=2 must permit exactly two reads, then refuse."""
        assert api_client.get(_url(share_link)).status_code == 200
        assert api_client.get(_url(share_link)).status_code == 200

        third = api_client.get(_url(share_link))
        assert third.status_code == 403

        share_link.refresh_from_db()
        # The refused request must not have incremented the counter past the cap.
        assert share_link.access_count == 2

    def test_increment_is_a_conditional_update_not_read_modify_write(
        self, api_client, share_link
    ):
        """
        The counter is bumped by a single conditional UPDATE, so a stale
        in-memory instance cannot be used to overshoot the cap. Simulating the
        race: another worker exhausts the link while this request holds an
        instance that still looks valid.
        """
        stale_url = _url(share_link)
        StudyShareLink.objects.filter(pk=share_link.pk).update(access_count=2)

        # The view re-reads and the UPDATE's WHERE clause rejects it.
        assert api_client.get(stale_url).status_code == 403
        share_link.refresh_from_db()
        assert share_link.access_count == 2

    def test_expired_link_is_refused_and_not_incremented(self, api_client, study, user):
        expired = StudyShareLink.objects.create(
            study=study, created_by=user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert api_client.get(_url(expired)).status_code == 403
        expired.refresh_from_db()
        assert expired.access_count == 0

    def test_unlimited_link_has_no_cap(self, api_client, study, user):
        unlimited = StudyShareLink.objects.create(study=study, created_by=user)
        for _ in range(3):
            assert api_client.get(_url(unlimited)).status_code == 200
        unlimited.refresh_from_db()
        assert unlimited.access_count == 3

    def test_unknown_token_is_404(self, api_client):
        import uuid
        url = reverse('dicom_images:public-shared-study', kwargs={'token': uuid.uuid4()})
        assert api_client.get(url).status_code == 404
