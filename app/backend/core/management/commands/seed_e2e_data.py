"""
Seed a deterministic user + AI model catalog for Playwright E2E tests.

Idempotent — safe to run repeatedly (e.g. once per CI job) without piling up
duplicate data. Does NOT create any studies/tasks/reports: the E2E suite
drives that through the real UI (upload -> dispatch -> webhook -> report) so
the test proves the actual workflow rather than pre-seeded fixtures.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command

E2E_EMAIL = 'e2e@vetimage.test'
E2E_PASSWORD = 'E2ePlaywright123!'


class Command(BaseCommand):
    help = "Seed the E2E test user and veterinary AI model catalog for Playwright."

    def handle(self, *args, **options):
        from users.models import User

        user, created = User.objects.get_or_create(
            email=E2E_EMAIL,
            defaults={'role': 1},  # Veterinarian
        )
        if created:
            user.set_password(E2E_PASSWORD)
            user.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(f"Created E2E user: {E2E_EMAIL}"))
        else:
            self.stdout.write(f"E2E user already exists: {E2E_EMAIL}")

        call_command('seed_vet_models')
        self.stdout.write(self.style.SUCCESS("E2E seed complete."))
