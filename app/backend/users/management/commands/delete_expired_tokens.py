"""
Delete Expired Tokens Command

Clean up expired JWT refresh tokens.
"""

from core.management.commands.base import BaseRichCommand
from core.services import CleanupService


class Command(BaseRichCommand):
    help = "Delete expired JWT refresh tokens from the blacklist"

    # Configuration
    requires_confirmation = False
    supports_dry_run = True
    use_atomic_transaction = True

    def execute(self, *args, **options):
        """Main command logic"""
        self.panel(
            "Delete Expired Tokens",
            "Cleaning up expired JWT refresh tokens"
        )

        summary = self.get_or_create_summary()

        # ========== Cleanup Tokens ==========
        self.info("\nCleaning up expired tokens...")

        result = CleanupService.cleanup_blacklisted_tokens(
            dry_run=self.is_dry_run
        )

        # Check if there was an error
        if 'error' in result:
            self.error(result['error'])
            self.warning(
                "Token blacklist app may not be installed. "
                "Ensure 'rest_framework_simplejwt.token_blacklist' is in INSTALLED_APPS."
            )
            return

        deleted_outstanding = result['deleted_outstanding']
        deleted_blacklisted = result['deleted_blacklisted']
        total_deleted = deleted_outstanding + deleted_blacklisted

        if self.is_dry_run:
            self.info(f"Would delete {deleted_outstanding} outstanding tokens")
            self.info(f"Would delete {deleted_blacklisted} blacklisted tokens")
            self.info(f"Total: {total_deleted} tokens")
        else:
            if total_deleted > 0:
                self.success(f"Deleted {deleted_outstanding} outstanding tokens")
                self.success(f"Deleted {deleted_blacklisted} blacklisted tokens")
                summary['deleted'] += total_deleted
            else:
                self.info("No expired tokens found")

        # ========== Display Statistics ==========
        if total_deleted > 0:
            self.print("\n")

            stats_rows = [
                ["Outstanding tokens deleted", str(deleted_outstanding)],
                ["Blacklisted tokens deleted", str(deleted_blacklisted)],
                ["Total deleted", str(total_deleted)],
            ]

            self.table(
                "Cleanup Statistics",
                ["Type", "Count"],
                stats_rows
            )

        # ========== Summary ==========
        self.print("\n")

        if self.is_dry_run:
            summary_content = (
                f"[yellow]DRY RUN - No changes made[/yellow]\n\n"
                f"Would delete:\n"
                f"  • {deleted_outstanding} outstanding tokens\n"
                f"  • {deleted_blacklisted} blacklisted tokens\n"
                f"  • {total_deleted} total tokens"
            )
        else:
            if total_deleted > 0:
                summary_content = (
                    f"[green]✓ Cleanup complete![/green]\n\n"
                    f"Deleted: {total_deleted} expired tokens\n\n"
                    f"[cyan]Details:[/cyan]\n"
                    f"  • Outstanding tokens: {deleted_outstanding}\n"
                    f"  • Blacklisted tokens: {deleted_blacklisted}"
                )
            else:
                summary_content = (
                    "[green]✓ No cleanup needed[/green]\n\n"
                    "No expired tokens found."
                )

        self.panel("Cleanup Summary", summary_content)

        # Display automation tip
        if not self.is_dry_run and total_deleted > 0:
            tip = (
                "To automate this cleanup, add to crontab:\n\n"
                "# Weekly cleanup on Sunday at 3 AM\n"
                "0 3 * * 0 cd /app/backend && "
                "python manage.py delete_expired_tokens --force"
            )
            self.panel("Automation Tip", tip, style="bold blue")
