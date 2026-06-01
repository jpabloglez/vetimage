"""
PDF Report Generator

Generates professional medical report PDFs using reportlab.
"""

from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


class PDFReportGenerator:
    """Generates PDF documents from Report model instances."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._register_custom_styles()

    def _register_custom_styles(self):
        """Register custom paragraph styles for medical reports."""
        self.styles.add(ParagraphStyle(
            'ReportTitle',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=6 * mm,
            textColor=colors.HexColor('#1e3a5f'),
        ))
        self.styles.add(ParagraphStyle(
            'SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=13,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
            textColor=colors.HexColor('#1e3a5f'),
            borderPadding=(0, 0, 2, 0),
        ))
        self.styles.add(ParagraphStyle(
            'Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            spaceBefore=8 * mm,
            italic=True,
        ))
        self.styles.add(ParagraphStyle(
            'FindingItem',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=10,
            spaceBefore=1 * mm,
        ))
        self.styles.add(ParagraphStyle(
            'ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            spaceAfter=4 * mm,
        ))

    def generate(self, report):
        """
        Generate a PDF from a Report instance.

        Args:
            report: Report model instance with populated ``content`` JSON.

        Returns:
            BytesIO buffer containing the PDF.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        story = []
        content = report.content or {}

        # Title
        story.append(Paragraph(report.title, self.styles['ReportTitle']))

        # Subtitle with report type and date
        generated_at = content.get('generated_at', '')
        report_type = content.get('report_type', 'Report')
        if generated_at:
            subtitle = f"{report_type} — Generated: {generated_at[:19]}"
        else:
            subtitle = report_type
        story.append(Paragraph(subtitle, self.styles['ReportSubtitle']))

        story.append(HRFlowable(
            width="100%", thickness=1,
            color=colors.HexColor('#1e3a5f'),
            spaceAfter=4 * mm,
        ))

        # Patient info table
        patient_info = content.get('patient_info', {})
        if patient_info:
            story.append(Paragraph('Patient Information', self.styles['SectionHeading']))
            story.append(self._build_info_table(patient_info))
            story.append(Spacer(1, 3 * mm))

        # Model info table
        model_info = content.get('model_info', {})
        if model_info:
            story.append(Paragraph('Model Information', self.styles['SectionHeading']))
            story.append(self._build_info_table(model_info))
            story.append(Spacer(1, 3 * mm))

        # Sections
        sections = content.get('sections', [])
        for section in sections:
            self._render_section(story, section)

        # Summary
        summary = content.get('summary', '')
        if summary:
            story.append(Paragraph('Summary', self.styles['SectionHeading']))
            story.append(Paragraph(summary, self.styles['Normal']))

        # Disclaimer
        disclaimer = content.get('disclaimer', '')
        if disclaimer:
            story.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.lightgrey,
                spaceBefore=6 * mm, spaceAfter=2 * mm,
            ))
            story.append(Paragraph(disclaimer, self.styles['Disclaimer']))

        doc.build(story)
        buffer.seek(0)
        return buffer

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_info_table(self, info_dict):
        """Build a two-column key/value table."""
        data = []
        for key, value in info_dict.items():
            label = key.replace('_', ' ').title()
            data.append([label, str(value)])

        if not data:
            return Spacer(1, 1)

        table = Table(data, colWidths=[55 * mm, 110 * mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e3a5f')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.lightgrey),
        ]))
        return table

    def _render_section(self, story, section):
        """Render a single report section."""
        title = section.get('title', 'Section')
        section_type = section.get('type', 'raw')

        story.append(Paragraph(title, self.styles['SectionHeading']))

        if section_type == 'findings':
            items = section.get('items', [])
            for item in items:
                if isinstance(item, dict):
                    text = item.get('description', item.get('text', str(item)))
                    confidence = item.get('confidence')
                    if confidence is not None:
                        text += f" (confidence: {confidence})"
                else:
                    text = str(item)
                story.append(Paragraph(f"• {text}", self.styles['FindingItem']))

        elif section_type == 'scores':
            data = section.get('data', {})
            if isinstance(data, dict):
                story.append(self._build_info_table(data))
            else:
                story.append(Paragraph(str(data), self.styles['Normal']))

        elif section_type in ('measurements', 'technical', 'raw'):
            data = section.get('data', {})
            if isinstance(data, dict):
                story.append(self._build_info_table(data))
            else:
                story.append(Paragraph(str(data), self.styles['Normal']))

        else:
            data = section.get('data', section.get('items', ''))
            story.append(Paragraph(str(data), self.styles['Normal']))

        story.append(Spacer(1, 2 * mm))
