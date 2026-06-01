"""
Cleanup Old Logs Command

Remove old Django sessions and log data.
"""

from core.management.commands.base import BaseRichCommand
from core.services import CleanupService


class Command(BaseRichCommand):
    help = "Clean up old Django sessions and expired data"

    # Configuration
    requires_confirmation = False
    supports_dry_run = True
    use_atomic_transaction = True

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        super().add_arguments(parser)

        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete sessions older than this many days (default: 30)'
        )

    def execute(self, *args, **options):
        """Main command logic"""
        days_old = options['days']

        self.panel(
            "Cleanup Old Logs",
            f"Removing sessions older than {days_old} days"
        )

        summary = self.get_or_create_summary()

        # ========== Cleanup Sessions ==========
        self.info(f"\nCleaning up sessions older than {days_old} days...")

        result = CleanupService.cleanup_old_sessions(
            days_old=days_old,
            dry_run=self.is_dry_run
        )

        deleted_count = result['deleted_count']
        cutoff_date = result['cutoff_date']

        if self.is_dry_run:
            self.info(f"Would delete {deleted_count} expired sessions")
            self.info(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            if deleted_count > 0:
                self.success(f"Deleted {deleted_count} expired sessions")
                summary['deleted'] += deleted_count
            else:
                self.info("No expired sessions found")

        # ========== Summary ==========
        self.print("\n")

        if self.is_dry_run:
            summary_content = (
                f"[yellow]DRY RUN - No changes made[/yellow]\n\n"
                f"Would delete: {deleted_count} sessions\n"
                f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}"
            )
        else:
            if deleted_count > 0:
                summary_content = (
                    f"[green]✓ Cleanup complete![/green]\n\n"
                    f"Deleted: {deleted_count} expired sessions\n"
                    f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}"
                )
            else:
                summary_content = (
                    "[green]✓ No cleanup needed[/green]\n\n"
                    "No expired sessions found."
                )

        self.panel("Cleanup Summary", summary_content)

        # Display automation tip
        if not self.is_dry_run and deleted_count > 0:
            tip = (
                "To automate this cleanup, add to crontab:\n\n"
                f"# Daily cleanup at 2 AM\n"
                f"0 2 * * * cd /app/backend && "
                f"python manage.py cleanup_old_logs --days={days_old} --force"
            )
            self.panel("Automation Tip", tip, style="bold blue")
