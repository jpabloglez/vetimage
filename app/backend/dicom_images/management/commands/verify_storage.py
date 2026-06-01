"""
Verify Storage Command

Check and fix user storage quota discrepancies.
"""

from core.management.commands.base import BaseRichCommand
from dicom_images.services import StorageVerificationService


class Command(BaseRichCommand):
    help = "Verify user storage quotas match actual usage"

    # Configuration
    requires_confirmation = False
    supports_dry_run = True
    use_atomic_transaction = True

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        super().add_arguments(parser)

        parser.add_argument(
            '--user-email',
            type=str,
            help='Check specific user by email'
        )

        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix quota discrepancies'
        )

    def execute(self, *args, **options):
        """Main command logic"""
        user_email = options.get('user_email')
        fix_mode = options.get('fix', False)

        self.panel(
            "Storage Quota Verification",
            "Comparing reported storage usage with actual file sizes"
        )

        # ========== Verify Single User or All Users ==========
        if user_email:
            # Verify specific user
            self.info(f"\nVerifying storage for user: {user_email}")

            from users.models import User
            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                self.error(f"User not found: {user_email}")
                return

            results = [StorageVerificationService.verify_user_quota(user)]
        else:
            # Verify all users
            self.info("\nVerifying storage for all users...")
            results = StorageVerificationService.verify_all_quotas()

            if not results:
                self.success("All user quotas are accurate!")
                return

            self.warning(f"Found {len(results)} users with quota discrepancies")

        # ========== Display Results ==========
        self.print("\n")

        # Format bytes for display
        def format_bytes(bytes_value):
            """Format bytes as human-readable string"""
            if bytes_value == 0:
                return "0 B"
            units = ['B', 'KB', 'MB', 'GB', 'TB']
            unit_index = 0
            value = float(bytes_value)
            while value >= 1024 and unit_index < len(units) - 1:
                value /= 1024
                unit_index += 1
            return f"{value:.2f} {units[unit_index]}"

        # Create table rows
        quota_rows = []
        for result in results:
            email = result['user_email']
            reported = format_bytes(result['reported_bytes'])
            actual = format_bytes(result['actual_bytes'])
            diff = format_bytes(abs(result['difference']))

            # Color code based on match
            if result['matches']:
                status = "[green]✓ Match[/green]"
            else:
                status = "[yellow]⚠ Mismatch[/yellow]"

            quota_rows.append([email, reported, actual, diff, status])

        self.table(
            "Storage Quota Verification Results",
            ["User Email", "Reported", "Actual", "Difference", "Status"],
            quota_rows,
            show_header=True
        )

        # ========== Fix Quotas ==========
        if fix_mode and results:
            self.print("\n")

            if self.is_dry_run:
                self.warning("Dry run mode - quotas will not be updated")
                fix_dry_run = True
            else:
                fix_dry_run = False

            self.info("Fixing quota discrepancies...")

            fixed_count = 0
            for result in results:
                if not result['matches']:
                    user = result['user']
                    fix_result = StorageVerificationService.fix_user_quota(
                        user=user,
                        dry_run=fix_dry_run
                    )

                    if fix_result['updated']:
                        old = format_bytes(fix_result['old_bytes'])
                        new = format_bytes(fix_result['new_bytes'])
                        self.success(
                            f"Updated {fix_result['user_email']}: "
                            f"{old} → {new}"
                        )
                        fixed_count += 1

            if self.is_dry_run:
                self.info(f"Would fix {fixed_count} user quotas")
            else:
                self.success(f"Fixed {fixed_count} user quotas")

        # ========== Summary ==========
        self.print("\n")

        if not results or all(r['matches'] for r in results):
            summary_content = (
                "[green]✓ All storage quotas are accurate![/green]\n\n"
                "No discrepancies found."
            )
        else:
            mismatches = len([r for r in results if not r['matches']])
            summary_content = (
                f"[yellow]⚠ Found {mismatches} quota discrepancies[/yellow]\n\n"
            )

            if fix_mode:
                if self.is_dry_run:
                    summary_content += "[blue]Run without --dry-run to apply fixes[/blue]"
                else:
                    summary_content += "[green]✓ Quotas have been corrected[/green]"
            else:
                summary_content += "[blue]Run with --fix to correct quotas[/blue]"

        self.panel("Verification Summary", summary_content)
