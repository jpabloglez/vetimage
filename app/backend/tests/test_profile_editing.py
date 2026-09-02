"""
Profile reading and editing.

`complete_profile` used to assign a default for every field it knew about, so
any client that omitted a key blanked it. Combined with a GET that never
returned those fields — meaning forms always prefilled empty — changing only
your language silently wiped your department, job title and team.
"""

import pytest
from django.urls import reverse


@pytest.fixture
def profile(user):
    from users.models import UserProfile
    p, _ = UserProfile.objects.get_or_create(user=user)
    p.department = 'Radiology'
    p.job_title = 'Radiologist'
    p.team_name = 'MRI Team'
    p.is_sharing_jobs_with_colleagues = True
    p.save()
    return p


COMPLETE = '/users/profile/complete_profile/'


@pytest.mark.django_db
class TestProfileIsReadable:

    def test_get_returns_the_editable_fields(self, auth_client, profile):
        """A settings form can only prefill what the API returns."""
        resp = auth_client.get(reverse('profile'))
        assert resp.status_code == 200
        block = resp.data['profile']
        assert block['department'] == 'Radiology'
        assert block['job_title'] == 'Radiologist'
        assert block['team_name'] == 'MRI Team'
        assert block['is_sharing_jobs_with_colleagues'] is True


@pytest.mark.django_db
class TestPartialUpdatesDoNotWipe:

    def test_language_only_save_preserves_everything_else(self, auth_client, profile):
        """The exact reported shape: open settings, change language, save."""
        resp = auth_client.post(COMPLETE, {'language': 'es'}, format='json')
        assert resp.status_code in (200, 201, 202)

        profile.refresh_from_db()
        assert profile.department == 'Radiology'
        assert profile.job_title == 'Radiologist'
        assert profile.team_name == 'MRI Team'
        assert profile.is_sharing_jobs_with_colleagues is True
        assert profile.language == 'es'

    def test_omitted_sharing_flag_is_not_reset(self, auth_client, profile):
        """It defaulted to False, so any partial save silently opted the user
        out of sharing their work with colleagues."""
        auth_client.post(COMPLETE, {'department': 'Cardiology'}, format='json')
        profile.refresh_from_db()
        assert profile.is_sharing_jobs_with_colleagues is True
        assert profile.department == 'Cardiology'

    def test_explicitly_clearing_a_field_still_works(self, auth_client, profile):
        """Partial semantics must not make fields unclearable."""
        auth_client.post(COMPLETE, {'team_name': ''}, format='json')
        profile.refresh_from_db()
        assert profile.team_name == ''
        assert profile.department == 'Radiology'

    def test_sharing_flag_can_be_turned_off_explicitly(self, auth_client, profile):
        auth_client.post(COMPLETE, {'is_sharing_jobs_with_colleagues': False}, format='json')
        profile.refresh_from_db()
        assert profile.is_sharing_jobs_with_colleagues is False

    def test_invalid_language_is_ignored(self, auth_client, profile):
        before = profile.language
        auth_client.post(COMPLETE, {'language': 'klingon'}, format='json')
        profile.refresh_from_db()
        assert profile.language == before
