"""
Tests for the files app image upload endpoint (POST /files/).

Covers the authentication gate and serializer validation. (A full
write-to-disk success path is exercised in integration, not unit, tests since
the static volume is read-only in the unit test container.)
"""
import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestImageUpload:
    def test_requires_authentication(self):
        resp = APIClient().post('/files/', {}, format='multipart')
        assert resp.status_code in (401, 403)

    def test_rejects_missing_image(self, auth_client):
        resp = auth_client.post('/files/', {}, format='multipart')
        assert resp.status_code == 400
        assert resp.data.get('detail') == 'Image upload failed'

    def test_rejects_non_image_file(self, auth_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        bogus = SimpleUploadedFile('note.txt', b'not an image', content_type='text/plain')
        resp = auth_client.post('/files/', {'image': bogus}, format='multipart')
        # ImageField validation rejects non-images before any disk write.
        assert resp.status_code == 400
