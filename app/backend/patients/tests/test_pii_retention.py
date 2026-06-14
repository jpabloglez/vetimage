"""
Tests for GDPR owner-PII retention: the anonymize_pii model method and the
purge_expired_pii management command.
"""
import pytest
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from patients.models import Owner


@pytest.mark.django_db
class TestOwnerAnonymize:
    def test_anonymize_pii_scrubs_fields_keeps_record(self, owner):
        owner_id = owner.id
        owner.anonymize_pii()
        owner.refresh_from_db()
        assert owner.id == owner_id  # record kept (study links survive)
        assert owner.first_name == '[redacted]'
        assert owner.last_name == '[redacted]'
        assert owner.email == ''
        assert owner.phone == ''
        assert owner.pii_anonymized is True


@pytest.mark.django_db
class TestPurgeCommand:
    def _run(self, **kwargs):
        out = StringIO()
        call_command('purge_expired_pii', stdout=out, **kwargs)
        return out.getvalue()

    def test_disabled_by_default(self, owner):
        # days defaults to OWNER_PII_RETENTION_DAYS (0 in tests) → no-op.
        out = self._run()
        assert 'disabled' in out.lower()
        owner.refresh_from_db()
        assert owner.pii_anonymized is False

    def test_dry_run_reports_without_modifying(self, owner):
        Owner.objects.filter(pk=owner.pk).update(updated_at=timezone.now() - timedelta(days=400))
        out = self._run(days=365, dry_run=True)
        assert 'dry-run' in out.lower()
        owner.refresh_from_db()
        assert owner.pii_anonymized is False

    def test_purges_stale_owner(self, owner):
        Owner.objects.filter(pk=owner.pk).update(updated_at=timezone.now() - timedelta(days=400))
        self._run(days=365)
        owner.refresh_from_db()
        assert owner.pii_anonymized is True
        assert owner.first_name == '[redacted]'

    def test_keeps_recent_owner(self, owner):
        # Updated just now → within window → untouched.
        self._run(days=365)
        owner.refresh_from_db()
        assert owner.pii_anonymized is False
