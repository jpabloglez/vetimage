"""
Tests for PDFReportGenerator service.
"""

import pytest
from reports.services.pdf_generator import PDFReportGenerator


@pytest.mark.django_db
class TestPDFReportGenerator:
    """Tests for the PDF generation service."""

    def setup_method(self):
        self.generator = PDFReportGenerator()

    def test_generate_returns_bytes(self, report):
        """generate() returns a BytesIO buffer with content."""
        buf = self.generator.generate(report)
        data = buf.read()
        assert len(data) > 0

    def test_pdf_magic_bytes(self, report):
        """Output starts with %PDF magic bytes."""
        buf = self.generator.generate(report)
        data = buf.read()
        assert data[:4] == b'%PDF'

    def test_generate_with_all_sections(self, report):
        """PDF is generated when report has all section types."""
        report.content['sections'] = [
            {'title': 'Findings', 'type': 'findings', 'items': ['Finding A']},
            {'title': 'Scores', 'type': 'scores', 'data': {'acc': 0.95}},
            {'title': 'Technical', 'type': 'technical', 'data': {'time': '12s'}},
        ]
        buf = self.generator.generate(report)
        data = buf.read()
        assert data[:4] == b'%PDF'
        assert len(data) > 100

    def test_generate_with_minimal_content(self, report):
        """PDF is generated even with minimal/empty content."""
        report.content = {}
        buf = self.generator.generate(report)
        data = buf.read()
        assert data[:4] == b'%PDF'
