"""
Report Template Engine

Applies templates to restructure report content.
"""

from reports.services.report_builder import ReportBuilder


class TemplateEngine:
    """Applies a ReportTemplate layout to report content."""

    def apply_template(self, template, task):
        """
        Build report content from task, then restructure per template layout.

        Args:
            template: ReportTemplate instance
            task: AnalysisTask instance

        Returns:
            dict: Structured report content with template applied.
        """
        builder = ReportBuilder()
        content = builder.build_from_task(task)

        layout = template.layout or {}

        # Filter and reorder sections
        section_defs = layout.get('sections', [])
        if section_defs:
            allowed_types = {s['type'] for s in section_defs}
            required_types = {s['type'] for s in section_defs if s.get('required', False)}
            order_map = {s['type']: s.get('order', 999) for s in section_defs}
            title_map = {s['type']: s.get('title') for s in section_defs}

            filtered = []
            for section in content.get('sections', []):
                stype = section.get('type')
                if stype in allowed_types:
                    # Override title if specified in template
                    if title_map.get(stype):
                        section['title'] = title_map[stype]
                    filtered.append(section)

            filtered.sort(key=lambda s: order_map.get(s.get('type'), 999))
            content['sections'] = filtered

        # Override disclaimer
        if layout.get('disclaimer'):
            content['disclaimer'] = layout['disclaimer']

        # Filter header fields (patient_info)
        header_fields = layout.get('header_fields')
        if header_fields and content.get('patient_info'):
            content['patient_info'] = {
                k: v for k, v in content['patient_info'].items()
                if k in header_fields
            }

        # Show/hide confidence
        if layout.get('show_confidence') is False:
            content['sections'] = [
                s for s in content.get('sections', [])
                if s.get('type') != 'scores'
            ]

        return content

    @staticmethod
    def get_default_templates():
        """
        Return 3 predefined template configurations.

        These are the layouts seeded by the seed_report_templates command.
        """
        return [
            {
                'name': 'Radiology Report',
                'template_type': 'radiology',
                'layout': {
                    'sections': [
                        {'key': 'findings', 'title': 'Findings', 'type': 'findings', 'required': True, 'order': 1},
                        {'key': 'measurements', 'title': 'Measurements', 'type': 'measurements', 'required': False, 'order': 2},
                        {'key': 'scores', 'title': 'Confidence', 'type': 'scores', 'required': False, 'order': 3},
                        {'key': 'technical', 'title': 'Technical Details', 'type': 'technical', 'required': False, 'order': 4},
                    ],
                    'disclaimer': (
                        'This radiology AI report is for research purposes only. '
                        'All findings must be reviewed by a board-certified radiologist.'
                    ),
                    'header_fields': ['patient_id', 'study_date', 'study_description'],
                    'show_confidence': True,
                },
            },
            {
                'name': 'Pathology Report',
                'template_type': 'pathology',
                'layout': {
                    'sections': [
                        {'key': 'findings', 'title': 'Pathological Findings', 'type': 'findings', 'required': True, 'order': 1},
                        {'key': 'scores', 'title': 'Classification Scores', 'type': 'scores', 'required': True, 'order': 2},
                    ],
                    'disclaimer': (
                        'This pathology AI report is for research purposes only. '
                        'Tissue analysis must be confirmed by a qualified pathologist.'
                    ),
                    'header_fields': ['patient_id', 'patient_name', 'study_date'],
                    'show_confidence': True,
                },
            },
            {
                'name': 'General Report',
                'template_type': 'general',
                'layout': {
                    'sections': [
                        {'key': 'findings', 'title': 'Findings', 'type': 'findings', 'required': True, 'order': 1},
                        {'key': 'scores', 'title': 'Confidence Scores', 'type': 'scores', 'required': False, 'order': 2},
                        {'key': 'measurements', 'title': 'Measurements', 'type': 'measurements', 'required': False, 'order': 3},
                        {'key': 'technical', 'title': 'Technical Details', 'type': 'technical', 'required': False, 'order': 4},
                    ],
                    'disclaimer': (
                        'This report was generated by an AI model and is intended '
                        'for research purposes only. All findings must be reviewed '
                        'by a qualified healthcare professional.'
                    ),
                    'header_fields': ['patient_id', 'patient_name', 'study_date', 'study_description'],
                    'show_confidence': True,
                },
            },
        ]
