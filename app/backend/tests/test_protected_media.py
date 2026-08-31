"""
Uploaded patient files must not be readable without a valid signature.

Everything under MEDIA_ROOT is clinical data (DICOM pixel data, clinical
photographs, lab PDFs). It was previously served by Django's `static()` helper
under DEBUG with no authorization at all, and in production depended entirely
on how the reverse proxy was configured.
"""

import time

import pytest
from django.urls import reverse

from core.protected_media import (
    MEDIA_URL_TTL_SECONDS as MEDIA_TTL,
    sign_media_path,
    signed_media_url,
)


@pytest.fixture
def media_file(tmp_path, settings):
    """Write a file into a temporary MEDIA_ROOT and return its relative path."""
    settings.MEDIA_ROOT = str(tmp_path)
    rel = 'patients/clinical/2026/08/wound.txt'
    full = tmp_path / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text('clinical photo bytes')
    return rel


def _url(rel, sig=None):
    base = reverse('protected-media', kwargs={'path': rel})
    return f'{base}?sig={sig}' if sig is not None else base


@pytest.mark.django_db
class TestProtectedMedia:

    def test_unsigned_request_is_refused(self, client, media_file):
        """The whole point: a bare path must not return the file."""
        resp = client.get(_url(media_file))
        assert resp.status_code == 403

    def test_forged_signature_is_refused(self, client, media_file):
        resp = client.get(_url(media_file, sig='not-a-real-signature'))
        assert resp.status_code == 403

    def test_signature_from_another_path_is_refused(self, client, media_file, tmp_path):
        """A signature is bound to its path and can't be replayed onto another."""
        other = 'patients/labs/secret.txt'
        (tmp_path / other).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / other).write_text('someone elses lab result')

        stolen = sign_media_path(media_file)
        resp = client.get(_url(other, sig=stolen))
        assert resp.status_code == 403

    def test_valid_signature_serves_the_file(self, client, media_file):
        resp = client.get(_url(media_file, sig=sign_media_path(media_file)))
        assert resp.status_code == 200
        assert b''.join(resp.streaming_content) == b'clinical photo bytes'

    def test_expired_signature_is_refused(self, client, media_file, monkeypatch):
        """A leaked link must stop working, not grant permanent access."""
        sig = sign_media_path(media_file)

        # Advance the clock the signer reads, rather than sleeping out the TTL.
        import django.core.signing as signing
        real_time = time.time()
        monkeypatch.setattr(
            signing, 'time',
            type('_t', (), {'time': staticmethod(
                lambda: real_time + MEDIA_TTL + 60)})(),
        )
        resp = client.get(_url(media_file, sig=sig))
        assert resp.status_code == 403

    def test_path_traversal_is_refused(self, client, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        outside = tmp_path.parent / 'outside.txt'
        outside.write_text('not yours')
        # Even correctly signed, an escaping path must be rejected.
        traversal = '../outside.txt'
        resp = client.get(_url(traversal, sig=sign_media_path(traversal)))
        assert resp.status_code in (403, 404)

    def test_missing_file_is_404_not_500(self, client, tmp_path, settings):
        settings.MEDIA_ROOT = str(tmp_path)
        rel = 'patients/labs/nope.pdf'
        resp = client.get(_url(rel, sig=sign_media_path(rel)))
        assert resp.status_code == 404

    def test_accel_redirect_is_used_when_configured(self, client, media_file, settings):
        """In production nginx should push the bytes, not Django."""
        settings.MEDIA_ACCEL_REDIRECT_PREFIX = '/internal-media/'
        resp = client.get(_url(media_file, sig=sign_media_path(media_file)))
        assert resp.status_code == 200
        assert resp['X-Accel-Redirect'] == f'/internal-media/{media_file}'



class TestSignedUrlHelper:

    def test_returns_none_for_empty_file_field(self):
        assert signed_media_url(None) is None
        assert signed_media_url('') is None

    def test_url_carries_a_signature(self, settings):
        class _F:
            name = 'patients/photos/rex.jpg'
        url = signed_media_url(_F())
        assert url.startswith(f'{settings.MEDIA_URL}patients/photos/rex.jpg?sig=')
