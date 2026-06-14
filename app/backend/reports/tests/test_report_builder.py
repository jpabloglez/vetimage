"""
Tests for ReportBuilder service.
"""

import pytest
from reports.services.report_builder import ReportBuilder


@pytest.mark.django_db
class TestReportBuilder:
    """Tests for the ReportBuilder service."""

    def setup_method(self):
        self.builder = ReportBuilder()

    def test_build_from_task_basic(self, completed_task):
        """build_from_task returns structured content with all required keys."""
        content = self.builder.build_from_task(completed_task)

        assert content['report_type'] == 'AI Analysis Report'
        assert 'generated_at' in content
        assert 'model_info' in content
        assert 'patient_info' in content
        assert 'sections' in content
        assert 'summary' in content
        assert 'disclaimer' in content

    def test_build_sections_with_findings(self, completed_task):
        """Sections include findings from result_metadata."""
        content = self.builder.build_from_task(completed_task)
        sections = content['sections']

        findings_section = next(
            (s for s in sections if s['type'] == 'findings'), None
        )
        assert findings_section is not None
        assert len(findings_section['items']) > 0

    def test_build_with_empty_metadata(self, completed_task):
        """Handles empty result_metadata gracefully."""
        completed_task.result_metadata = {}
        completed_task.save()

        content = self.builder.build_from_task(completed_task)
        assert content['sections'] == []

    def test_model_info_included(self, completed_task):
        """Model info contains name, key, version, and type."""
        content = self.builder.build_from_task(completed_task)
        model_info = content['model_info']

        assert model_info['name'] == 'Test Model'
        assert model_info['key'] == 'test-model-v1'
        assert model_info['version'] == '1.0'
        assert 'type' in model_info

    def test_build_summary(self, completed_task):
        """Summary includes model name and finding count."""
        content = self.builder.build_from_task(completed_task)
        summary = content['summary']

        assert 'Test Model' in summary
        assert '1 finding' in summary

    def test_build_from_vet_thorax_finding_shape(self, completed_task):
        """The vet AI pipeline's finding shape (label/region/confidence/description
        in result_metadata.findings) flows into a findings section, and the
        human-readable description is preserved for owner/referral rendering."""
        completed_task.result_metadata = {
            'findings': [
                {'label': 'cardiomegaly', 'region': 'cardiac', 'confidence': 0.83,
                 'description': 'Possible cardiomegaly (cardiac), confidence 83%.'},
                {'label': 'pleural_effusion', 'region': 'pleural_space', 'confidence': 0.61,
                 'description': 'Possible pleural effusion (pleural space), confidence 61%.'},
            ],
            'model_version': 'vet-thorax-fixture-0.1.0',
        }
        completed_task.save()

        content = self.builder.build_from_task(completed_task)
        findings_section = next((s for s in content['sections'] if s['type'] == 'findings'), None)
        assert findings_section is not None
        assert len(findings_section['items']) == 2
        descriptions = [i.get('description') for i in findings_section['items']]
        assert any('cardiomegaly' in (d or '') for d in descriptions)
        assert '2 finding(s)' in content['summary']
