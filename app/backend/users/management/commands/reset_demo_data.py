"""
Reset Demo Data Command

Clear user-generated data and restore clean demo state.
"""

from core.management.commands.base import BaseRichCommand
from users.services import UserCreationService
from dicom_images.services import DicomDataGenerationService


class Command(BaseRichCommand):
    help = "Reset database to clean demo state - removes all user data and recreates demo users"

    # Configuration
    requires_confirmation = True  # Destructive operation
    supports_dry_run = True
    use_atomic_transaction = True

    def add_arguments(self, parser):
        """Add command-specific arguments"""
        super().add_arguments(parser)

        parser.add_argument(
            '--keep-superusers',
            action='store_true',
            help='Keep superuser accounts (delete only regular users)'
        )

    def execute(self, *args, **options):
        """Main command logic"""
        keep_superusers = options.get('keep_superusers', False)

        # Display warning
        self.panel(
            "⚠️  Reset Demo Data",
            "[red]WARNING: This will delete all user data![/red]\n\n"
            "This command will:\n"
            "  • Delete all non-superuser accounts (or all if --keep-superusers not set)\n"
            "  • Delete all DICOM studies (cascades to series and images)\n"
            "  • Delete all user storage quotas\n"
            "  • Recreate demo users and sample data\n\n"
            "[yellow]This operation cannot be undone![/yellow]"
        )

        if self.is_dry_run:
            self.warning("\nDry run mode - no changes will be made")

        # ========== Count Existing Data ==========
        from users.models import User, UserProfile, Organization
        from dicom_images.models import MedicalStudy, UserStorageQuota

        if keep_superusers:
            users_to_delete = User.objects.filter(is_superuser=False)
        else:
            users_to_delete = User.objects.all()

        user_count = users_to_delete.count()
        study_count = MedicalStudy.objects.filter(uploaded_by__in=users_to_delete).count()
        quota_count = UserStorageQuota.objects.filter(user__in=users_to_delete).count()

        # Display what will be deleted
        delete_rows = [
            ["Users", str(user_count)],
            ["Studies (with series & images)", str(study_count)],
            ["Storage Quotas", str(quota_count)],
        ]

        self.table(
            "Data to be Deleted",
            ["Type", "Count"],
            delete_rows
        )

        if self.is_dry_run:
            self.info("\nWould delete this data and recreate demo users")
            return

        summary = self.get_or_create_summary()

        # ========== Delete Existing Data ==========
        self.info("\nDeleting existing data...")

        # Delete users (cascades to profiles, organizations, studies)
        deleted_users = user_count
        users_to_delete.delete()
        self.success(f"Deleted {deleted_users} users")
        summary['deleted'] += deleted_users

        # Clean up orphaned quotas (should be handled by cascade, but just in case)
        orphaned_quotas = UserStorageQuota.objects.filter(user__isnull=True)
        deleted_quotas = orphaned_quotas.count()
        if deleted_quotas > 0:
            orphaned_quotas.delete()
            self.info(f"Cleaned up {deleted_quotas} orphaned quotas")
            summary['deleted'] += deleted_quotas

        # ========== Recreate Demo Data ==========
        self.info("\nRecreating demo users...")

        try:
            demo_users = UserCreationService.create_demo_users(count=3)
            self.success(f"Created {len(demo_users)} demo users")
            summary['created'] += len(demo_users)

            # Display demo users
            user_rows = []
            for user in demo_users:
                try:
                    profile = user.userprofile
                    name = f"{profile.first_name} {profile.last_name}"
                except:
                    name = "N/A"
                user_rows.append([user.email, name, "demo123"])

            self.table(
                "Demo Users Created",
                ["Email", "Name", "Password"],
                user_rows
            )

        except Exception as e:
            self.error(f"Failed to create demo users: {e}")
            summary['errors'] += 1
            return

        # ========== Create Sample DICOM Data ==========
        self.info("\nGenerating sample DICOM studies...")

        modalities = ['CT', 'MR']
        studies_created = 0

        with self.progress("Creating sample data") as progress:
            task = progress.add_task(
                "[cyan]Generating studies...",
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
                        self.warning(f"Failed to create {modality} study: {e}")
                        summary['errors'] += 1
                        progress.advance(task)

        self.success(f"Generated {studies_created} sample studies")
        summary['created'] += studies_created

        # ========== Summary ==========
        self.print("\n")

        summary_content = (
            f"[green]✓ Demo data reset complete![/green]\n\n"
            f"[bold]Deleted:[/bold]\n"
            f"  • {deleted_users} users\n"
            f"  • {study_count} studies\n\n"
            f"[bold]Created:[/bold]\n"
            f"  • {len(demo_users)} demo users\n"
            f"  • {studies_created} sample studies\n\n"
            f"[cyan]Demo user password:[/cyan] demo123\n"
        )

        if summary['errors'] > 0:
            summary_content += f"\n[yellow]⚠ {summary['errors']} errors occurred[/yellow]"

        self.panel("Reset Summary", summary_content)

        # Display next steps
        next_steps = (
            "1. Login with demo users (password: demo123)\n"
            "2. Test API endpoints with fresh data\n"
            "3. View studies in OHIF Viewer\n"
            "4. Run: python manage.py setup_project (for more data)"
        )
        self.panel("Next Steps", next_steps, style="bold blue")
