"""
Audit Trail Report Generator

Queries AuditLog entries and produces structured reports / PDF output.
"""

import logging
from collections import Counter
from django.utils import timezone

from credentials.models import AuditLog

logger = logging.getLogger(__name__)


class AuditReportService:
    """Build structured audit trail reports from AuditLog data."""

    def query_logs(self, filters):
        """
        Query AuditLog with filters.

        *filters* may contain: date_from, date_to, user_id, event_type,
        risk_score_min.

        Returns a QuerySet.
        """
        qs = AuditLog.objects.all().order_by('-event_timestamp')

        if filters.get('date_from'):
            qs = qs.filter(event_timestamp__gte=filters['date_from'])
        if filters.get('date_to'):
            qs = qs.filter(event_timestamp__lte=filters['date_to'])
        if filters.get('user_id'):
            qs = qs.filter(user_id=filters['user_id'])
        if filters.get('event_type'):
            qs = qs.filter(event_type=filters['event_type'])
        if filters.get('risk_score_min') is not None:
            qs = qs.filter(risk_score__gte=filters['risk_score_min'])

        return qs

    def build_audit_report(self, filters, user):
        """
        Build a structured JSON report matching the Report content schema.

        Returns a dict with: report_type, generated_at, sections, summary,
        disclaimer.
        """
        logs = self.query_logs(filters)
        total = logs.count()

        # Event breakdown
        event_counts = Counter(logs.values_list('event_type', flat=True))

        # High-risk events
        high_risk = logs.filter(risk_score__gte=70)
        high_risk_count = high_risk.count()

        # Suspicious events
        suspicious_count = logs.filter(is_suspicious=True).count()

        # Build sections
        sections = [
            {
                'title': 'Summary Statistics',
                'type': 'scores',
                'data': {
                    'total_events': total,
                    'high_risk_events': high_risk_count,
                    'suspicious_events': suspicious_count,
                    'unique_users': logs.values('user_id').distinct().count(),
                },
            },
            {
                'title': 'Event Breakdown',
                'type': 'measurements',
                'data': dict(event_counts.most_common(20)),
            },
        ]

        if high_risk_count > 0:
            high_risk_items = [
                {
                    'description': (
                        f"{log.event_type} by "
                        f"{log.user.email if log.user else log.username_attempted} "
                        f"at {log.event_timestamp.isoformat()} "
                        f"(risk: {log.risk_score})"
                    ),
                    'confidence': log.risk_score / 100.0,
                }
                for log in high_risk[:10]
            ]
            sections.append({
                'title': 'High-Risk Events',
                'type': 'findings',
                'items': high_risk_items,
            })

        return {
            'report_type': 'Audit Trail Report',
            'generated_at': timezone.now().isoformat(),
            'patient_info': {},
            'model_info': {},
            'sections': sections,
            'summary': (
                f"Audit trail report covering {total} events. "
                f"{high_risk_count} high-risk and {suspicious_count} suspicious "
                f"events detected."
            ),
            'disclaimer': (
                'This audit report is generated for compliance and monitoring '
                'purposes. It covers authentication and authorization events '
                'as recorded by the system.'
            ),
        }

    def generate_pdf(self, filters, user):
        """
        Generate a PDF audit report.

        Returns a BytesIO buffer containing the PDF.
        """
        from reports.services.pdf_generator import PDFReportGenerator

        content = self.build_audit_report(filters, user)

        # Build a report-like object for the PDF generator
        class _ReportProxy:
            def __init__(self, title, content):
                self.title = title
                self.content = content

        report_proxy = _ReportProxy(
            title='Audit Trail Report',
            content=content,
        )

        generator = PDFReportGenerator()
        return generator.generate(report_proxy)
