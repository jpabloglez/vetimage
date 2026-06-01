"""
Setup Project Command

One-command setup for new developers.
Creates superuser, demo users, and sample DICOM data.
"""

from core.management.commands.base import BaseRichCommand
from users.services import UserCreationService
from dicom_images.services import DicomDataGenerationService


class Command(BaseRichCommand):
    help = "Setup project for development - creates superuser, demo users, and sample data"

    # Configuration
    requires_confirmation = False
    supports_dry_run = True
    use_atomic_transaction = True

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        super().add_arguments(parser)

        parser.add_argument(
            '--superuser-email',
            type=str,
            default='admin@example.com',
            help='Email for superuser account (default: admin@example.com)'
        )

        parser.add_argument(
            '--superuser-password',
            type=str,
            default='admin123',
            help='Password for superuser account (default: admin123)'
        )

        parser.add_argument(
            '--demo-users',
            type=int,
            default=3,
            help='Number of demo users to create (default: 3)'
        )

        parser.add_argument(
            '--skip-sample-data',
            action='store_true',
            help='Skip creating sample DICOM studies'
        )

    def execute(self, *args, **options):
        """Main command logic"""
        from users.models import User

        # Display welcome panel
        self.panel(
            "Project Setup",
            "Setting up development environment\n"
            "This will create users and sample data for testing"
        )

        # Parse options
        superuser_email = options['superuser_email']
        superuser_password = options['superuser_password']
        demo_users_count = options['demo_users']
        skip_sample_data = options['skip_sample_data']

        summary = self.get_or_create_summary()

        # ========== Create Superuser ==========
        self.info("Creating superuser account...")

        if self.is_dry_run:
            self.print(f"  Would create superuser: {superuser_email}")
            summary['created'] += 1
        else:
            # Check if superuser already exists
            if User.objects.filter(email=superuser_email).exists():
                self.warning(f"Superuser {superuser_email} already exists, skipping")
                summary['skipped'] += 1
                superuser = User.objects.get(email=superuser_email)
            else:
                superuser = UserCreationService.create_superuser(
                    email=superuser_email,
                    password=superuser_password
                )
                self.success(f"Created superuser: {superuser_email}")
                self.info(f"  Password: {superuser_password}")
                summary['created'] += 1

        # ========== Create Demo Users ==========
        demo_users = []

        if demo_users_count > 0:
            self.info(f"\nCreating {demo_users_count} demo users...")

            if self.is_dry_run:
                self.print(f"  Would create {demo_users_count} demo users")
                summary['created'] += demo_users_count
            else:
                try:
                    demo_users = UserCreationService.create_demo_users(count=demo_users_count)
                    self.success(f"Created {len(demo_users)} demo users")

                    # Display demo users
                    if demo_users:
                        user_rows = []
                        for user in demo_users:
                            try:
                                profile = user.userprofile
                                name = f"{profile.first_name} {profile.last_name}"
                            except:
                                name = "N/A"
                            user_rows.append([user.email, name, "demo123"])

                        self.table(
                            "Demo Users",
                            ["Email", "Name", "Password"],
                            user_rows
                        )

                    summary['created'] += len(demo_users)
                except Exception as e:
                    self.error(f"Failed to create demo users: {e}")
                    summary['errors'] += 1

        # ========== Create Sample DICOM Data ==========
        if not skip_sample_data and demo_users:
            self.info("\nGenerating sample DICOM studies...")

            modalities = ['CT', 'MR', 'CR']

            if self.is_dry_run:
                total_studies = len(demo_users) * len(modalities)
                self.print(f"  Would create {total_studies} sample studies")
                summary['created'] += total_studies
            else:
                studies_created = 0

                with self.progress("Generating DICOM studies") as progress:
                    task = progress.add_task(
                        "[cyan]Creating studies...",
                        total=len(demo_users) * len(modalities)
                    )

                    for user in demo_users:
                        for modality in modalities:
                            try:
                                study = DicomDataGenerationService.generate_study(
                                    user=user,
                                    modality=modality,
                                    num_series=2,
                                    num_images_per_series=5
                                )
                                studies_created += 1
                                progress.advance(task)
                            except Exception as e:
                                self.warning(f"Failed to create {modality} study for {user.email}: {e}")
                                summary['errors'] += 1
                                progress.advance(task)

                self.success(f"Generated {studies_created} sample studies")
                self.info("  Each demo user has CT, MR, and CR studies")
                summary['created'] += studies_created

        # ========== Display Summary ==========
        self.print("\n")  # Add spacing

        if self.is_dry_run:
            summary_content = (
                f"[yellow]DRY RUN - No changes made[/yellow]\n\n"
                f"[green]Would create:[/green]\n"
                f"  • 1 superuser ({superuser_email})\n"
                f"  • {demo_users_count} demo users\n"
            )
            if not skip_sample_data:
                summary_content += f"  • {demo_users_count * 3} DICOM studies\n"
        else:
            summary_content = (
                f"[green]✓ Setup complete![/green]\n\n"
                f"[bold]Superuser:[/bold]\n"
                f"  • Email: {superuser_email}\n"
                f"  • Password: {superuser_password}\n\n"
            )

            if demo_users:
                summary_content += (
                    f"[bold]Demo Users:[/bold]\n"
                    f"  • Count: {len(demo_users)}\n"
                    f"  • Password: demo123 (all users)\n"
                )

                if not skip_sample_data:
                    total_images = len(demo_users) * 3 * 2 * 5  # users * modalities * series * images
                    summary_content += (
                        f"\n[bold]Sample Data:[/bold]\n"
                        f"  • Studies: {len(demo_users) * 3}\n"
                        f"  • Total Images: {total_images}\n"
                    )

        self.panel("Setup Summary", summary_content)

        # Display next steps
        if not self.is_dry_run:
            next_steps = (
                "1. Start the backend: docker-compose up\n"
                "2. Access Django admin: http://localhost:3080/admin/\n"
                "3. Test API endpoints with demo users\n"
                "4. View DICOM data in OHIF Viewer"
            )
            self.panel("Next Steps", next_steps, style="bold blue")
