"""
Anonymize Data Command

GDPR-compliant user data anonymization.
"""

from core.management.commands.base import BaseRichCommand
from users.services import AnonymizationService


class Command(BaseRichCommand):
    help = "Anonymize user personal data for GDPR compliance"

    # Configuration
    requires_confirmation = True  # Destructive operation
    supports_dry_run = True
    use_atomic_transaction = True

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        super().add_arguments(parser)

        parser.add_argument(
            '--email',
            type=str,
            help='Anonymize specific user by email'
        )

        parser.add_argument(
            '--inactive-days',
            type=int,
            default=365,
            help='Anonymize users inactive for this many days (default: 365)'
        )

        parser.add_argument(
            '--keep-studies',
            action='store_true',
            help='Keep studies but anonymize patient names (default: delete studies)'
        )

    def execute(self, *args, **options):
        """Main command logic"""
        user_email = options.get('email')
        inactive_days = options['inactive_days']
        keep_studies = options.get('keep_studies', False)

        # Display warning
        warning_text = (
            "[red]WARNING: This will permanently anonymize user data![/red]\n\n"
            "This operation will:\n"
            "  • Replace user email with anonymized_[id]@example.com\n"
            "  • Set user account as inactive\n"
            "  • Clear all personal information from profile\n"
        )

        if keep_studies:
            warning_text += "  • Anonymize patient names in DICOM studies\n"
        else:
            warning_text += "  • Delete all DICOM studies and images\n"

        warning_text += "\n[yellow]This operation cannot be undone![/yellow]"

        self.panel("⚠️  GDPR Data Anonymization", warning_text)

        if self.is_dry_run:
            self.warning("\nDry run mode - no changes will be made")

        summary = self.get_or_create_summary()

        # ========== Single User Anonymization ==========
        if user_email:
            self.info(f"\nAnonymizing user: {user_email}")

            from users.models import User
            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                self.error(f"User not found: {user_email}")
                return

            # Check if user is superuser
            if user.is_superuser:
                self.error("Cannot anonymize superuser accounts")
                self.warning("Remove superuser status first if you really want to anonymize")
                return

            if self.is_dry_run:
                self.info(f"Would anonymize user: {user_email}")
                self.info(f"  User ID: {user.id}")
                self.info(f"  Keep studies: {keep_studies}")
                return

            try:
                result = AnonymizationService.anonymize_user(
                    user_id=user.id,
                    keep_studies=keep_studies
                )

                self.success(f"Anonymized user {result['user_id']}")
                self.info(f"  Original email: {result['original_email']}")
                self.info(f"  New email: {result['new_email']}")
                self.info(f"  Studies deleted: {result['studies_deleted']}")
                self.info(f"  Studies anonymized: {result['studies_anonymized']}")

                summary['updated'] += 1

            except Exception as e:
                self.error(f"Failed to anonymize user: {e}")
                summary['errors'] += 1

        # ========== Bulk Anonymization ==========
        else:
            self.info(f"\nSearching for users inactive for {inactive_days}+ days...")

            result = AnonymizationService.anonymize_inactive_users(
                inactive_days=inactive_days,
                dry_run=True  # Always dry run first to show what will be affected
            )

            found_count = result['found_count']
            user_ids = result['user_ids']

            if found_count == 0:
                self.success("No inactive users found matching criteria")
                return

            # Display users to be anonymized
            self.warning(f"Found {found_count} inactive users")

            from users.models import User
            users_to_show = User.objects.filter(id__in=user_ids[:10])

            user_rows = []
            for user in users_to_show:
                last_login = user.last_login.strftime('%Y-%m-%d') if user.last_login else 'Never'
                user_rows.append([str(user.id), user.email, last_login])

            self.table(
                f"Inactive Users (showing up to 10 of {found_count})",
                ["ID", "Email", "Last Login"],
                user_rows
            )

            if self.is_dry_run:
                self.info(f"\nWould anonymize {found_count} users")
                self.info(f"Keep studies: {keep_studies}")
                return

            # Confirm bulk operation
            if not self.confirm(f"Anonymize {found_count} inactive users?"):
                self.info("Operation cancelled by user")
                return

            # Perform bulk anonymization
            self.info(f"\nAnonymizing {found_count} users...")

            with self.progress("Anonymizing users") as progress:
                task = progress.add_task(
                    "[cyan]Processing...",
                    total=found_count
                )

                for user_id in user_ids:
                    try:
                        AnonymizationService.anonymize_user(
                            user_id=user_id,
                            keep_studies=keep_studies
                        )
                        summary['updated'] += 1
                        progress.advance(task)
                    except Exception as e:
                        self.warning(f"Failed to anonymize user {user_id}: {e}")
                        summary['errors'] += 1
                        progress.advance(task)

            self.success(f"Anonymized {summary['updated']} users")

        # ========== Summary ==========
        self.print("\n")

        if self.is_dry_run:
            if user_email:
                summary_content = (
                    f"[yellow]DRY RUN - No changes made[/yellow]\n\n"
                    f"Would anonymize user: {user_email}"
                )
            else:
                summary_content = (
                    f"[yellow]DRY RUN - No changes made[/yellow]\n\n"
                    f"Would anonymize: {found_count} inactive users\n"
                    f"Inactive threshold: {inactive_days} days\n"
                    f"Keep studies: {keep_studies}"
                )
        else:
            if user_email:
                summary_content = (
                    f"[green]✓ User anonymized![/green]\n\n"
                    f"Email: {user_email}\n"
                    f"Studies: {'Anonymized' if keep_studies else 'Deleted'}"
                )
            else:
                summary_content = (
                    f"[green]✓ Bulk anonymization complete![/green]\n\n"
                    f"Users anonymized: {summary['updated']}\n"
                    f"Studies: {'Anonymized' if keep_studies else 'Deleted'}\n"
                )

                if summary['errors'] > 0:
                    summary_content += f"\n[yellow]⚠ {summary['errors']} errors occurred[/yellow]"

        self.panel("Anonymization Summary", summary_content)

        # Display GDPR compliance note
        if not self.is_dry_run and summary['updated'] > 0:
            gdpr_note = (
                "[bold]GDPR Compliance:[/bold]\n"
                "  • User accounts set to inactive\n"
                "  • Personal data removed from profiles\n"
                "  • Email addresses anonymized\n"
                "  • Original data cannot be recovered\n\n"
                "[cyan]Documentation:[/cyan]\n"
                "  • Log this action for compliance records\n"
                "  • Keep backup if required by retention policy\n"
                "  • Notify data protection officer if applicable"
            )
            self.panel("GDPR Compliance", gdpr_note, style="bold blue")
