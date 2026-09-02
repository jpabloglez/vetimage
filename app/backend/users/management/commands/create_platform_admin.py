"""
Create (or promote) a VetImage platform administrator.

Platform admins can read across every clinic, so this deliberately has no UI:
the only way to grant it is shell access to the server. Nothing in the API can
set `is_staff`.

Distinct from `createsuperuser`, which also sets `is_superuser` — that grants
every Django permission implicitly, which the admin panel needs none of. This
command grants exactly `is_staff` and nothing more.

    python manage.py create_platform_admin alice@vetimage.app
    python manage.py create_platform_admin alice@vetimage.app --revoke
"""

import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Grant or revoke VetImage platform-admin access (is_staff).'

    def add_arguments(self, parser):
        parser.add_argument('email', help='Account to grant/revoke access for.')
        parser.add_argument(
            '--revoke', action='store_true',
            help='Remove platform-admin access instead of granting it.',
        )
        parser.add_argument(
            '--password',
            help='Password for a new account. Prompted for if omitted.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        email = options['email'].strip().lower()

        if options['revoke']:
            return self._revoke(email)

        user = User.objects.filter(email__iexact=email).first()
        if user:
            if user.is_staff:
                self.stdout.write(f'{email} is already a platform admin.')
                return
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            self.stdout.write(self.style.SUCCESS(f'Granted platform admin to {email}.'))
            return

        password = options.get('password') or getpass.getpass('Password: ')
        if not password:
            raise CommandError('A password is required to create a new account.')

        user = User.objects.create_user(email=email, password=password)
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        self.stdout.write(self.style.SUCCESS(f'Created platform admin {email}.'))

    def _revoke(self, email):
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise CommandError(f'No account found for {email}.')
        if not user.is_staff:
            self.stdout.write(f'{email} is not a platform admin.')
            return
        user.is_staff = False
        user.save(update_fields=['is_staff'])
        self.stdout.write(self.style.SUCCESS(f'Revoked platform admin from {email}.'))
