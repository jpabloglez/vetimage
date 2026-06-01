"""
Check Data Integrity Command

Verify database integrity and find orphaned records.
"""

from core.management.commands.base import BaseRichCommand
from core.services import DataIntegrityService


class Command(BaseRichCommand):
    help = "Check database integrity and find orphaned records"

    # Configuration
    requires_confirmation = False
    supports_dry_run = False  # Just checking, not modifying
    use_atomic_transaction = False

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        super().add_arguments(parser)

        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically delete orphaned records'
        )

        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation when using --fix'
        )

    def execute(self, *args, **options):
        """Main command logic"""
        fix_mode = options.get('fix', False)

        self.panel(
            "Data Integrity Check",
            "Scanning database for orphaned records and invalid references"
        )

        # ========== Check Orphaned Records ==========
        self.info("\nChecking for orphaned records...")

        orphaned = DataIntegrityService.check_orphaned_records()

        orphan_rows = [
            ["Series without study", orphaned['orphaned_series']],
            ["Images without series", orphaned['orphaned_images']],
            ["Annotations without image", orphaned['orphaned_annotations']],
            ["User profiles without user", orphaned['orphaned_profiles']],
        ]

        self.table(
            "Orphaned Records",
            ["Type", "Count"],
            orphan_rows
        )

        total_orphaned = sum(orphaned.values())

        if total_orphaned == 0:
            self.success("No orphaned records found!")
        else:
            self.warning(f"Found {total_orphaned} orphaned records")

        # ========== Check File References ==========
        self.info("\nChecking file references...")

        invalid_files = DataIntegrityService.check_invalid_file_references()

        file_rows = [
            ["Missing DICOM files", invalid_files['missing_dicom_files']],
            ["Missing thumbnails", invalid_files['missing_thumbnails']],
        ]

        self.table(
            "Invalid File References",
            ["Type", "Count"],
            file_rows
        )

        total_missing = (
            invalid_files['missing_dicom_files'] +
            invalid_files['missing_thumbnails']
        )

        if total_missing == 0:
            self.success("All file references are valid!")
        else:
            self.warning(f"Found {total_missing} missing files")

            if invalid_files['invalid_file_paths']:
                self.info("\nSample missing files:")
                for path in invalid_files['invalid_file_paths'][:5]:
                    self.print(f"  • {path}", style="dim")
                if len(invalid_files['invalid_file_paths']) > 5:
                    remaining = len(invalid_files['invalid_file_paths']) - 5
                    self.print(f"  ... and {remaining} more", style="dim")

        # ========== Fix Orphaned Records ==========
        if fix_mode and total_orphaned > 0:
            self.print("\n")

            # Ask for confirmation unless --force
            if not options.get('force', False):
                if not self.confirm(
                    f"Delete {total_orphaned} orphaned records?"
                ):
                    self.info("Cancelled by user")
                    return

            self.info("Deleting orphaned records...")

            results = DataIntegrityService.fix_orphaned_records(dry_run=False)

            fix_rows = [
                ["Series deleted", results['deleted_series']],
                ["Images deleted", results['deleted_images']],
                ["Annotations deleted", results['deleted_annotations']],
                ["Profiles deleted", results['deleted_profiles']],
            ]

            self.table(
                "Cleanup Results",
                ["Type", "Deleted"],
                fix_rows
            )

            total_deleted = sum(results.values())
            self.success(f"Deleted {total_deleted} orphaned records")

        # ========== Summary ==========
        self.print("\n")

        if total_orphaned == 0 and total_missing == 0:
            summary_content = (
                "[green]✓ Database integrity is good![/green]\n\n"
                "No issues found."
            )
        else:
            summary_content = (
                f"[yellow]⚠ Issues detected[/yellow]\n\n"
                f"Orphaned records: {total_orphaned}\n"
                f"Missing files: {total_missing}\n"
            )

            if fix_mode and total_orphaned > 0:
                summary_content += f"\n[green]✓ Orphaned records cleaned up[/green]"
            elif total_orphaned > 0:
                summary_content += (
                    f"\n[blue]Run with --fix to clean up orphaned records[/blue]"
                )

            if total_missing > 0:
                summary_content += (
                    f"\n[yellow]Note: Missing files must be restored manually[/yellow]"
                )

        self.panel("Integrity Check Summary", summary_content)
