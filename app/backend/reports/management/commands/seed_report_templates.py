"""
Management command to seed default report templates.
"""

from django.core.management.base import BaseCommand

from reports.models import ReportTemplate
from reports.services.template_engine import TemplateEngine


class Command(BaseCommand):
    help = 'Seed default report templates (radiology, pathology, general)'

    def handle(self, *args, **options):
        defaults = TemplateEngine.get_default_templates()
        created = 0

        for tpl_data in defaults:
            _, was_created = ReportTemplate.objects.get_or_create(
                name=tpl_data['name'],
                is_default=True,
                defaults={
                    'template_type': tpl_data['template_type'],
                    'layout': tpl_data['layout'],
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {created} new default template(s) '
                f'({len(defaults) - created} already existed).'
            )
        )
