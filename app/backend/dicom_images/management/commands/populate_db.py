"""
Populate Database Command

Generate realistic test data at scale for development and testing.
"""

from core.management.commands.base import BaseRichCommand
from users.services import UserCreationService
from dicom_images.services import DicomDataGenerationService


class Command(BaseRichCommand):
    help = "Populate database with test data - users, studies, series, and images"

    # Configuration
    requires_confirmation = True  # This creates a lot of data
    supports_dry_run = True
    use_atomic_transaction = True

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        super().add_arguments(parser)

        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create (default: 10)'
        )

        parser.add_argument(
            '--studies-per-user',
            type=int,
            default=5,
            help='Number of studies per user (default: 5)'
        )

        parser.add_argument(
            '--series-per-study',
            type=int,
            default=3,
            help='Number of series per study (default: 3)'
        )

        parser.add_argument(
            '--images-per-series',
            type=int,
            default=10,
            help='Number of images per series (default: 10)'
        )

    def execute(self, *args, **options):
        """Main command logic"""
        # Parse options
        num_users = options['users']
        studies_per_user = options['studies_per_user']
        series_per_study = options['series_per_study']
        images_per_series = options['images_per_series']

        # Calculate totals
        total_studies = num_users * studies_per_user
        total_series = total_studies * series_per_study
        total_images = total_series * images_per_series

        # Display what will be created
        preview_content = (
            f"[cyan]Users:[/cyan] {num_users}\n"
            f"[cyan]Studies per user:[/cyan] {studies_per_user}\n"
            f"[cyan]Series per study:[/cyan] {series_per_study}\n"
            f"[cyan]Images per series:[/cyan] {images_per_series}\n\n"
            f"[bold yellow]Total to create:[/bold yellow]\n"
            f"  • {total_studies:,} Studies\n"
            f"  • {total_series:,} Series\n"
            f"  • {total_images:,} Images\n"
        )
        self.panel("Population Plan", preview_content)

        if self.is_dry_run:
            self.warning("Dry run mode - no data will be created")
            return

        summary = self.get_or_create_summary()

        # ========== Create Users ==========
        self.info(f"\nCreating {num_users} demo users...")

        try:
            users = UserCreationService.create_demo_users(count=num_users)
            self.success(f"Created {len(users)} users")
            summary['created'] += len(users)
        except Exception as e:
            self.error(f"Failed to create users: {e}")
            summary['errors'] += 1
            return

        # ========== Generate DICOM Studies ==========
        self.info(f"\nGenerating DICOM studies...")

        modalities = ['CT', 'MR', 'CR', 'DX']
        studies_created = 0
        errors = 0

        with self.progress("Generating DICOM data") as progress:
            # Create progress bar
            task = progress.add_task(
                "[cyan]Creating studies...",
                total=total_studies
            )

            for user in users:
                for study_num in range(studies_per_user):
                    # Cycle through modalities
                    modality = modalities[study_num % len(modalities)]

                    try:
                        study = DicomDataGenerationService.generate_study(
                            user=user,
                            modality=modality,
                            num_series=series_per_study,
                            num_images_per_series=images_per_series
                        )
                        studies_created += 1
                        progress.advance(task)
                    except Exception as e:
                        self.warning(f"Failed to create study: {e}")
                        errors += 1
                        summary['errors'] += 1
                        progress.advance(task)

        self.success(f"Generated {studies_created} studies")
        summary['created'] += studies_created

        if errors > 0:
            self.warning(f"Encountered {errors} errors during generation")

        # ========== Display Statistics ==========
        self.print("\n")

        # Create statistics table
        actual_series = studies_created * series_per_study
        actual_images = actual_series * images_per_series

        stats_rows = [
            ["Users", str(len(users))],
            ["Studies", f"{studies_created:,}"],
            ["Series", f"{actual_series:,}"],
            ["Images (metadata only)", f"{actual_images:,}"],
        ]

        self.table(
            "Database Population Statistics",
            ["Entity", "Count"],
            stats_rows
        )

        # Display summary
        summary_content = (
            f"[green]✓ Database populated successfully![/green]\n\n"
            f"[bold]Created:[/bold]\n"
            f"  • {len(users)} users\n"
            f"  • {studies_created:,} studies\n"
            f"  • {actual_series:,} series\n"
            f"  • {actual_images:,} image records\n\n"
            f"[yellow]Note:[/yellow] Image records created without actual DICOM files.\n"
            f"Use this for testing database schema and API endpoints."
        )

        if summary['errors'] > 0:
            summary_content += f"\n\n[red]⚠ {summary['errors']} errors occurred[/red]"

        self.panel("Population Complete", summary_content)

        # Display usage tips
        tips = (
            "1. Test search: python manage.py shell\n"
            "2. Query data: MedicalStudy.objects.count()\n"
            "3. View in admin: http://localhost:3080/admin/\n"
            "4. Reset data: python manage.py reset_demo_data --force"
        )
        self.panel("Next Steps", tips, style="bold blue")
