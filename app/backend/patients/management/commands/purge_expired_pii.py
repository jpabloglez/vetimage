"""
GDPR data-retention: anonymize owner PII that has passed the retention window.

Owners not updated within `OWNER_PII_RETENTION_DAYS` (settings/env) have their
personal data scrubbed (name/email/phone/address) while the record and its
study links are kept. Disabled when the retention setting is 0/unset.

Usage:
    python manage.py purge_expired_pii            # apply
    python manage.py purge_expired_pii --dry-run  # report only
    python manage.py purge_expired_pii --days 365 # override window
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from patients.models import Owner


class Command(BaseCommand):
    help = 'Anonymize owner PII older than the configured retention window (GDPR).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report without modifying data')
        parser.add_argument('--days', type=int, default=None, help='Override retention window (days)')

    def handle(self, *args, **options):
        days = options['days']
        if days is None:
            days = int(getattr(settings, 'OWNER_PII_RETENTION_DAYS', 0) or 0)

        if days <= 0:
            self.stdout.write(self.style.WARNING(
                'PII retention is disabled (OWNER_PII_RETENTION_DAYS=0). Nothing to do.'
            ))
            return

        cutoff = timezone.now() - timedelta(days=days)
        stale = Owner.objects.filter(pii_anonymized=False, updated_at__lt=cutoff)
        count = stale.count()

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE(
                f'[dry-run] {count} owner(s) older than {days} days would be anonymized.'
            ))
            return

        for owner in stale.iterator():
            owner.anonymize_pii()

        self.stdout.write(self.style.SUCCESS(
            f'Anonymized PII for {count} owner(s) older than {days} days.'
        ))
