"""
Content-Security-Policy: enforcement, the docs-only widening, and the
violation-report endpoint.

Background, because it explains what these tests are guarding. The policy
shipped report-only with a comment saying to enforce it "once a report-only run
is clean" — but neither policy carried a `report-uri`, so violations went to
whichever browser console happened to be open and no such run was observable.
Driving a real browser over the admin, Swagger UI, ReDoc, the DRF browsable API
and every SPA route (including the Cornerstone viewer, which decodes DICOM into
blobs and runs codecs in workers) found exactly three violations, all on the
two docs pages: Swagger's CDN favicon, ReDoc's CDN logo, and a blob-backed
worker spawned by redoc.standalone.js.

The tests that matter most here are the ones asserting what the base policy
must *not* contain. The docs widening is scoped to two URLs precisely so the
Django admin keeps the tight policy; folding it into the base would relax the
admin to suit a docs page, which is how a CSP ends up nominally present and
worthless.
"""

import json

import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

REPORT_URL = '/api/csp-report/'


def _csp(resp):
    return resp.get('Content-Security-Policy') or resp.get('Content-Security-Policy-Report-Only', '')


@pytest.mark.django_db
class TestTheBasePolicyStaysTight:
    """Everything that is not the API docs — the admin above all."""

    def test_it_is_enforced_not_merely_reported(self, api_client):
        resp = api_client.get(reverse('health-liveness'))
        assert 'Content-Security-Policy' in resp
        assert 'Content-Security-Policy-Report-Only' not in resp

    def test_it_does_not_allow_blob_workers(self, api_client):
        """ReDoc needs these; the admin has no business running one."""
        assert "worker-src 'none'" in _csp(api_client.get(reverse('health-liveness')))

    def test_it_does_not_allow_cdn_images(self, api_client):
        csp = _csp(api_client.get(reverse('health-liveness')))
        img = next(d for d in csp.split('; ') if d.startswith('img-src'))
        assert 'cdn.jsdelivr.net' not in img
        assert 'cdn.redoc.ly' not in img

    def test_it_keeps_the_directives_that_do_the_work(self, api_client):
        csp = _csp(api_client.get(reverse('health-liveness')))
        for directive in ("default-src 'self'", "frame-ancestors 'none'",
                          "object-src 'none'", "base-uri 'self'",
                          "form-action 'self'"):
            assert directive in csp

    def test_violations_are_reported_somewhere(self, api_client):
        """
        The whole reason this sat unenforced. Without report-uri, an enforced
        policy fails silently — a blocked resource just doesn't load.
        """
        assert f'report-uri {settings.CSP_REPORT_PATH}' in _csp(
            api_client.get(reverse('health-liveness'))
        )


@pytest.mark.django_db
class TestTheDocsPagesGetExactlyWhatTheyNeed:

    @pytest.mark.parametrize('url_name', ['api-docs', 'api-redoc'])
    def test_the_measured_violations_are_covered(self, api_client, url_name):
        csp = _csp(api_client.get(reverse(url_name)))
        # Swagger's favicon and ReDoc's logo.
        assert 'cdn.jsdelivr.net' in csp
        assert 'cdn.redoc.ly' in csp
        # redoc.standalone.js spawns a worker from a blob URL.
        assert "worker-src 'self' blob:" in csp

    def test_the_widening_does_not_leak_to_other_pages(self, api_client):
        """A prefix match on two URLs, not a global relaxation."""
        docs = _csp(api_client.get(reverse('api-docs')))
        other = _csp(api_client.get(reverse('health-liveness')))
        assert docs != other
        assert 'cdn.redoc.ly' not in other

    @pytest.mark.parametrize('url_name', ['api-docs', 'api-redoc'])
    def test_the_docs_policy_is_still_enforced(self, api_client, url_name):
        resp = api_client.get(reverse(url_name))
        assert 'Content-Security-Policy' in resp
        assert 'Content-Security-Policy-Report-Only' not in resp


@pytest.mark.django_db
class TestReportOnlyRemainsAvailable:
    """The escape hatch for shaking out a new directive before committing."""

    @override_settings(CSP_ENFORCE=False)
    def test_disabling_enforcement_falls_back_to_report_only(self, api_client):
        resp = api_client.get(reverse('health-liveness'))
        assert 'Content-Security-Policy-Report-Only' in resp
        assert 'Content-Security-Policy' not in resp


@pytest.mark.django_db
class TestTheReportEndpoint:
    """
    Posted to by browsers we do not control, and reachable by anyone who finds
    the URL. It must be impossible to turn into noise or into a 500.
    """

    def test_it_accepts_the_report_uri_shape(self, api_client, caplog):
        body = {'csp-report': {
            'effective-directive': 'img-src',
            'blocked-uri': 'https://evil.test/x.png',
            'document-uri': 'http://localhost:3081/api/docs/',
            'disposition': 'enforce',
        }}
        resp = api_client.post(
            REPORT_URL, data=json.dumps(body), content_type='application/csp-report',
        )
        assert resp.status_code == 204
        assert 'img-src' in caplog.text

    def test_it_accepts_the_reporting_api_shape(self, api_client, caplog):
        """Chrome posts application/reports+json with different field names."""
        body = [{
            'type': 'csp-violation',
            'url': 'http://localhost:3001/dashboard',
            'body': {
                'effectiveDirective': 'connect-src',
                'blockedURL': 'https://evil.test/beacon',
                'disposition': 'enforce',
            },
        }]
        resp = api_client.post(
            REPORT_URL, data=json.dumps(body), content_type='application/reports+json',
        )
        assert resp.status_code == 204
        assert 'connect-src' in caplog.text

    @pytest.mark.parametrize('payload', ['not json', '[]', 'null', '{"unexpected": 1}', ''])
    def test_junk_never_becomes_an_error(self, api_client, payload):
        """
        A 500 here would be noise in exactly the channel this exists to keep
        readable — and a browser has nothing useful to do with an error.
        """
        resp = api_client.post(
            REPORT_URL, data=payload, content_type='application/csp-report',
        )
        assert resp.status_code == 204

    def test_it_needs_no_authentication(self, api_client):
        """The browser posts these with no credentials, by design."""
        resp = api_client.post(
            REPORT_URL,
            data=json.dumps({'csp-report': {'effective-directive': 'img-src'}}),
            content_type='application/csp-report',
        )
        assert resp.status_code == 204

    def test_hostile_field_values_are_truncated(self, api_client, caplog):
        """Every field is attacker-controlled; none of it goes in whole."""
        from core.csp_report import MAX_FIELD

        body = {'csp-report': {
            'effective-directive': 'img-src',
            'blocked-uri': 'https://evil.test/' + ('A' * 5000),
        }}
        api_client.post(
            REPORT_URL, data=json.dumps(body), content_type='application/csp-report',
        )
        assert 'A' * (MAX_FIELD + 50) not in caplog.text

    def test_a_batch_cannot_be_unbounded(self, api_client, caplog):
        """One POST must not be able to write thousands of log lines."""
        body = [{
            'type': 'csp-violation',
            'body': {'effectiveDirective': f'directive-{i}', 'blockedURL': 'x'},
        } for i in range(500)]
        resp = api_client.post(
            REPORT_URL, data=json.dumps(body), content_type='application/reports+json',
        )
        assert resp.status_code == 204
        assert 'directive-400' not in caplog.text

    def test_an_unexpected_content_type_is_ignored(self, api_client):
        resp = api_client.post(
            REPORT_URL, data='<xml/>', content_type='application/xml',
        )
        assert resp.status_code == 204
