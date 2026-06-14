"""
Tests for the Report Templates system.
"""

import pytest
from rest_framework.test import APIClient

from reports.models import ReportTemplate
from reports.services.template_engine import TemplateEngine


@pytest.fixture
def default_templates(db):
    """Seed default templates for tests."""
    templates = []
    for tpl_data in TemplateEngine.get_default_templates():
        t = ReportTemplate.objects.create(
            name=tpl_data['name'],
            template_type=tpl_data['template_type'],
            layout=tpl_data['layout'],
            is_default=True,
        )
        templates.append(t)
    return templates


@pytest.fixture
def custom_template(user):
    """Create a custom user template."""
    return ReportTemplate.objects.create(
        name='My Custom Template',
        template_type='custom',
        layout={
            'sections': [
                {'key': 'findings', 'title': 'Findings', 'type': 'findings', 'required': True, 'order': 1},
            ],
            'disclaimer': 'Custom disclaimer text.',
            'show_confidence': False,
        },
        is_default=False,
        created_by=user,
    )


@pytest.mark.django_db
class TestReportTemplateService:

    def test_get_default_templates(self):
        """TemplateEngine returns the veterinary default template configs."""
        defaults = TemplateEngine.get_default_templates()
        assert len(defaults) == 3
        types = {d['template_type'] for d in defaults}
        assert types == {'radiology', 'general'}
        # All veterinary templates require veterinarian sign-off.
        assert all(d['layout'].get('requires_signoff') for d in defaults)

    def test_apply_radiology(self, completed_task, default_templates):
        """Radiology template filters and reorders sections; vet disclaimer applied."""
        radiology = next(t for t in default_templates if t.template_type == 'radiology')
        engine = TemplateEngine()
        content = engine.apply_template(radiology, completed_task)

        assert 'sections' in content
        assert content['disclaimer'].startswith('Veterinary decision support')

    def test_filters_sections(self, completed_task, default_templates):
        """The Thoracic (VHS) template excludes the technical section."""
        vhs = next(t for t in default_templates if 'VHS' in t.name)
        engine = TemplateEngine()
        content = engine.apply_template(vhs, completed_task)

        section_types = {s['type'] for s in content['sections']}
        assert 'technical' not in section_types

    def test_custom_disclaimer(self, completed_task, custom_template):
        """Custom template disclaimer overrides the default."""
        engine = TemplateEngine()
        content = engine.apply_template(custom_template, completed_task)
        assert content['disclaimer'] == 'Custom disclaimer text.'


@pytest.mark.django_db
class TestReportTemplateAPI:

    def test_list_includes_defaults(self, auth_client, default_templates):
        """GET /api/reports/templates/ includes defaults."""
        response = auth_client.get('/api/reports/templates/')
        assert response.status_code == 200
        assert len(response.data['results']) >= 3

    def test_create_custom(self, auth_client):
        """POST creates a custom template."""
        response = auth_client.post('/api/reports/templates/', {
            'name': 'Test Template',
            'template_type': 'custom',
            'layout': {'sections': []},
        }, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'Test Template'
        assert response.data['is_default'] is False

    def test_update_custom(self, auth_client, custom_template):
        """PUT updates a custom template."""
        response = auth_client.put(
            f'/api/reports/templates/{custom_template.id}/',
            {
                'name': 'Updated Name',
                'template_type': 'custom',
                'layout': {'sections': []},
            },
            format='json',
        )
        assert response.status_code == 200
        assert response.data['name'] == 'Updated Name'

    def test_delete_custom(self, auth_client, custom_template):
        """DELETE removes a custom template."""
        response = auth_client.delete(
            f'/api/reports/templates/{custom_template.id}/'
        )
        assert response.status_code == 204

    def test_cannot_delete_system(self, auth_client, default_templates):
        """Cannot DELETE a system default template."""
        tpl = default_templates[0]
        response = auth_client.delete(f'/api/reports/templates/{tpl.id}/')
        assert response.status_code == 400

    def test_defaults_action(self, auth_client, default_templates):
        """GET /api/reports/templates/defaults/ returns only defaults."""
        response = auth_client.get('/api/reports/templates/defaults/')
        assert response.status_code == 200
        assert all(t['is_default'] for t in response.data)

    def test_create_report_with_template(self, auth_client, completed_task, default_templates):
        """Can create a report using a template."""
        tpl = default_templates[0]
        response = auth_client.post('/api/reports/', {
            'analysis_task_id': str(completed_task.id),
            'template_id': str(tpl.id),
        }, format='json')
        assert response.status_code == 201
        assert response.data['content']['disclaimer'].startswith('Veterinary decision support')


@pytest.mark.django_db
class TestReportTemplateSpeciesModalityFiltering:
    BASE = '/api/reports/templates/'

    def _create(self, auth_client, name, template_type='general',
                species=None, modality=None):
        return auth_client.post(self.BASE, {
            'name': name,
            'template_type': template_type,
            'layout': {},
            'species_filter': species or [],
            'modality_filter': modality or [],
        }, format='json')

    def test_filter_by_species_returns_matching_and_unfiltered(self, auth_client):
        self._create(auth_client, 'Canine Only', species=['canine'])
        self._create(auth_client, 'All Species', species=[])
        self._create(auth_client, 'Feline Only', species=['feline'])

        resp = auth_client.get(f'{self.BASE}?species=canine')
        assert resp.status_code == 200
        names = [t['name'] for t in (resp.data.get('results', resp.data))]
        assert 'Canine Only' in names
        assert 'All Species' in names
        assert 'Feline Only' not in names

    def test_filter_by_modality_returns_matching_and_unfiltered(self, auth_client):
        self._create(auth_client, 'CR Template', modality=['CR'])
        self._create(auth_client, 'Any Modality', modality=[])
        self._create(auth_client, 'US Only', modality=['US'])

        resp = auth_client.get(f'{self.BASE}?modality=CR')
        assert resp.status_code == 200
        names = [t['name'] for t in (resp.data.get('results', resp.data))]
        assert 'CR Template' in names
        assert 'Any Modality' in names
        assert 'US Only' not in names

    def test_new_vet_template_types_accepted(self, auth_client):
        new_types = [
            'thoracic_canine', 'thoracic_feline', 'thoracic_equine',
            'abdominal_us', 'orthopedic', 'dental', 'cardiac_vhs',
            'discharge_summary', 'vaccination_certificate',
            'referral_letter', 'soap_note',
        ]
        for ttype in new_types:
            resp = self._create(auth_client, f'Test {ttype}', template_type=ttype)
            assert resp.status_code == 201, f"Failed for {ttype}: {resp.content}"

    def test_species_and_modality_included_in_response(self, auth_client):
        resp = self._create(
            auth_client, 'Canine Thorax',
            template_type='thoracic_canine',
            species=['canine'], modality=['CR', 'DX'],
        )
        assert resp.status_code == 201, resp.content
        assert resp.data['species_filter'] == ['canine']
        assert resp.data['modality_filter'] == ['CR', 'DX']
