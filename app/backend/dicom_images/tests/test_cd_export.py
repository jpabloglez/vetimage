"""
Tests for the DICOM CD/USB export endpoint.

The shared `image` fixture's file is not a valid DICOM dataset, so these tests
exercise the plain-tree fallback path; FileSet/DICOMDIR generation is a
best-effort layer on top of it.
"""
import io
import zipfile

import pytest


@pytest.mark.django_db
class TestStudyCDExport:
    def _url(self, study):
        return f'/api/dicom/studies/{study.study_instance_uid}/export/'

    def test_export_returns_zip_with_dicom_tree(self, auth_client, study, image):
        resp = auth_client.get(self._url(study))
        assert resp.status_code == 200, resp.content
        assert resp['Content-Type'] == 'application/zip'
        assert 'attachment' in resp['Content-Disposition']

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert 'README.txt' in names
        # Fallback layout: the instance lands under DICOM/
        assert any(n.startswith('DICOM/') and n.endswith('.dcm') for n in names)

    def test_export_empty_study_still_returns_zip(self, auth_client, study):
        resp = auth_client.get(self._url(study))
        assert resp.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        assert 'README.txt' in zf.namelist()

    def test_export_unknown_study_404(self, auth_client):
        resp = auth_client.get('/api/dicom/studies/9.9.9.9.9/export/')
        assert resp.status_code == 404

    def test_export_cross_org_404(self, api_client, other_user, study):
        """A user from a different (lazily provisioned) org cannot export the study."""
        api_client.force_authenticate(user=other_user)
        resp = api_client.get(self._url(study))
        assert resp.status_code == 404

    def test_export_requires_auth(self, api_client, study):
        resp = api_client.get(self._url(study))
        assert resp.status_code in (401, 403)
