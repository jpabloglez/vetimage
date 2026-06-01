"""
Check DICOM Metadata Command

Validate DICOM files against database records.
"""

from core.management.commands.base import BaseRichCommand
from dicom_images.services import DicomMetadataValidationService


class Command(BaseRichCommand):
    help = "Validate DICOM files and metadata integrity"

    # Configuration
    requires_confirmation = False
    supports_dry_run = False  # Just validation, not modification
    use_atomic_transaction = False

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        super().add_arguments(parser)

        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of files to check (default: all)'
        )

    def execute(self, *args, **options):
        """Main command logic"""
        limit = options.get('limit')

        if limit:
            self.panel(
                "DICOM Metadata Validation",
                f"Validating up to {limit:,} DICOM files"
            )
        else:
            self.panel(
                "DICOM Metadata Validation",
                "Validating all DICOM files in database"
            )

        # ========== Validate DICOM Files ==========
        self.info("\nValidating DICOM files...")

        from dicom_images.models import MedicalImage

        total_count = MedicalImage.objects.count()
        check_count = min(limit, total_count) if limit else total_count

        self.info(f"Total images in database: {total_count:,}")
        self.info(f"Checking: {check_count:,}\n")

        # Run validation with progress bar
        with self.progress("Validating files") as progress:
            task = progress.add_task(
                "[cyan]Checking DICOM files...",
                total=check_count
            )

            # Get images to check
            images = MedicalImage.objects.all()
            if limit:
                images = images[:limit]

            valid_count = 0
            invalid_count = 0
            invalid_details = []

            for image in images:
                result = DicomMetadataValidationService.validate_dicom_file(image)

                if result['valid']:
                    valid_count += 1
                else:
                    invalid_count += 1
                    invalid_details.append(result)

                progress.advance(task)

        # ========== Display Results ==========
        self.print("\n")

        # Summary statistics
        stats_rows = [
            ["Total checked", str(check_count)],
            ["Valid files", str(valid_count)],
            ["Invalid files", str(invalid_count)],
            ["Validation rate", f"{(valid_count/check_count*100):.1f}%" if check_count > 0 else "N/A"],
        ]

        self.table(
            "Validation Statistics",
            ["Metric", "Value"],
            stats_rows
        )

        # Show invalid files if any
        if invalid_count > 0:
            self.warning(f"\nFound {invalid_count} invalid files")

            # Display first 10 invalid files
            display_count = min(10, len(invalid_details))

            invalid_rows = []
            for detail in invalid_details[:display_count]:
                image_id = str(detail['image_id'])
                sop_uid = detail['sop_uid'][:30] + "..." if len(detail['sop_uid']) > 30 else detail['sop_uid']
                error_summary = detail['errors'][0] if detail['errors'] else "Unknown error"
                if len(error_summary) > 50:
                    error_summary = error_summary[:47] + "..."

                invalid_rows.append([image_id, sop_uid, error_summary])

            self.table(
                f"Invalid Files (showing {display_count} of {invalid_count})",
                ["Image ID", "SOP UID", "Error"],
                invalid_rows
            )

            # Show detailed errors for first few files
            if invalid_details:
                self.print("\nDetailed errors for first invalid file:")
                first_invalid = invalid_details[0]
                self.print(f"  Image ID: {first_invalid['image_id']}", style="cyan")
                self.print(f"  SOP UID: {first_invalid['sop_uid']}", style="cyan")
                self.print(f"  File Path: {first_invalid['file_path']}", style="cyan")
                self.print("  Errors:", style="yellow")
                for error in first_invalid['errors']:
                    self.print(f"    • {error}", style="dim")

        else:
            self.success("\nAll checked files are valid!")

        # ========== Summary ==========
        self.print("\n")

        if invalid_count == 0:
            summary_content = (
                "[green]✓ All DICOM files validated successfully![/green]\n\n"
                f"Checked {check_count:,} files with no issues."
            )
        else:
            summary_content = (
                f"[yellow]⚠ Validation issues found[/yellow]\n\n"
                f"Valid: {valid_count:,}\n"
                f"Invalid: {invalid_count:,}\n"
                f"Success rate: {(valid_count/check_count*100):.1f}%\n\n"
                f"[blue]Common issues:[/blue]\n"
                f"  • Missing files on disk\n"
                f"  • SOP Instance UID mismatch\n"
                f"  • Dimension mismatch\n"
                f"  • Missing required DICOM tags\n\n"
                f"[yellow]Note:[/yellow] Invalid files may need to be re-uploaded."
            )

        self.panel("Validation Summary", summary_content)

        # Return non-zero exit code if invalid files found
        if invalid_count > 0:
            raise SystemExit(1)
