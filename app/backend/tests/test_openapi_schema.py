"""
OpenAPI / API documentation contract tests.

Locks in that the schema generates, the interactive docs are served, the JWT
'Authorize' security scheme is present, and the key (veterinary) endpoints are
documented. These guard against regressions in the API-docs setup.
"""
import pytest
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator


@pytest.fixture(scope='module')
def schema():
    """Generate the OpenAPI schema once (also asserts generation doesn't raise)."""
    return SchemaGenerator().get_schema(request=None, public=True)


@pytest.mark.django_db
class TestOpenAPISchema:
    def test_schema_generates_and_is_openapi3(self, schema):
        assert schema['openapi'].startswith('3.')
        assert schema['info']['title'].startswith('VetImage')

    def test_bearer_auth_scheme_is_defined(self, schema):
        """The Swagger 'Authorize' button needs a defined bearerAuth scheme."""
        schemes = schema['components']['securitySchemes']
        assert 'bearerAuth' in schemes
        assert schemes['bearerAuth']['type'] == 'http'
        assert schemes['bearerAuth']['scheme'] == 'bearer'

    @pytest.mark.parametrize('path_prefix', [
        '/api/patients/owners/',
        '/api/patients/animals/',
        '/api/patients/vhs/',
        '/api/ai-analysis/models/',
        '/users/auth/login/',
        '/api/health/',
    ])
    def test_key_paths_documented(self, schema, path_prefix):
        assert any(p.startswith(path_prefix) for p in schema['paths']), \
            f'{path_prefix} missing from OpenAPI schema'

    def test_owner_share_and_public_report_documented(self, schema):
        paths = schema['paths']
        assert any('/share' in p for p in paths)
        assert any('/shared/' in p for p in paths)

    def test_veterinary_tags_present(self, schema):
        tag_names = {t['name'] for t in schema.get('tags', [])}
        assert {'Patients', 'VHS', 'Reports'}.issubset(tag_names)

    def test_supported_species_in_aimodel_schema(self, schema):
        """The species-aware field should be part of the documented AIModel."""
        comps = schema['components']['schemas']
        # Find any AIModel component and assert supported_species is a property.
        ai_models = {k: v for k, v in comps.items() if 'AIModel' in k}
        assert ai_models, 'No AIModel schema component found'
        assert any('supported_species' in (v.get('properties') or {}) for v in ai_models.values())


@pytest.mark.django_db
class TestDocsEndpoints:
    def test_schema_endpoint_200(self, client):
        resp = client.get(reverse('api-schema'))
        assert resp.status_code == 200

    def test_swagger_ui_200(self, client):
        resp = client.get(reverse('api-docs'))
        assert resp.status_code == 200

    def test_redoc_200(self, client):
        resp = client.get(reverse('api-redoc'))
        assert resp.status_code == 200
