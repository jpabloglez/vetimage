"""
Django Management Command: Generate Statistics Test Data

Creates realistic dummy data for testing the Statistics page including:
- Analysis tasks with various statuses
- Patient demographics (ID, age, sex)
- DICOM metadata (modality, body part, study info)
- Processing times and timestamps
- Multiple AI models

Usage:
    python manage.py generate_statistics_data --count 100
    python manage.py generate_statistics_data --count 50 --days 30
    python manage.py generate_statistics_data --clean
"""

import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from ai_analysis.models import AnalysisTask, AIModel
from dicom_images.models import MedicalStudy, MedicalSeries, MedicalImage

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate dummy statistics data for testing the Statistics page'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of tasks to generate (default: 50)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Distribute tasks over last N days (default: 30)',
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete all existing analysis tasks before generating new ones',
        )

    def handle(self, *args, **options):
        count = options['count']
        days = options['days']
        clean = options['clean']

        self.stdout.write(self.style.SUCCESS(
            f'\nGenerating {count} dummy analysis tasks distributed over {days} days...\n'
        ))

        # Clean existing data if requested
        if clean:
            self.stdout.write('Cleaning existing analysis tasks...')
            deleted_count = AnalysisTask.objects.all().count()
            AnalysisTask.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing tasks\n'))

        # Get or create test user
        user, created = User.objects.get_or_create(
            email='test@openmedlab.com',
            defaults={'password': 'test123', 'role': 1}
        )
        if created:
            user.set_password('test123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created test user: {user.email}'))

        # Ensure we have AI models
        models = list(AIModel.objects.filter(is_active=True))
        if not models:
            self.stdout.write(self.style.ERROR(
                'No active AI models found. Please create AI models first.'
            ))
            return

        self.stdout.write(f'Found {len(models)} active AI models\n')

        # Get or create a single medical image for all tasks
        # (In real usage, there would be different images, but for testing this is fine)
        study, _ = MedicalStudy.objects.get_or_create(
            study_instance_uid='1.2.840.test.dummy.study',
            defaults={
                'patient_id': 'DUMMY001',
                'patient_name': 'Test^Dummy^Patient',
                'uploaded_by': user,
            }
        )

        series, _ = MedicalSeries.objects.get_or_create(
            study=study,
            series_instance_uid='1.2.840.test.dummy.series',
            defaults={
                'series_number': 1,
            }
        )

        medical_image, _ = MedicalImage.objects.get_or_create(
            series=series,
            sop_instance_uid='1.2.840.test.dummy.image',
            defaults={
                'instance_number': 1,
            }
        )

        # Data for generation
        statuses = ['COMPLETED', 'FAILED', 'PROCESSING', 'QUEUED', 'PENDING']
        status_weights = [60, 15, 10, 10, 5]  # 60% completed, 15% failed, etc.

        modalities = ['CT', 'MRI', 'US', 'XR', 'MG', 'PET', 'NM']
        body_parts = [
            'BRAIN', 'CHEST', 'ABDOMEN', 'PELVIS', 'SPINE',
            'HEAD', 'NECK', 'LEG', 'ARM', 'HEART', 'LIVER'
        ]
        patient_sexes = ['M', 'F', 'O']

        # Generate tasks
        tasks_created = 0

        for i in range(count):
            try:
                # Random timestamp within the last N days
                days_ago = random.randint(0, days)
                hours_ago = random.randint(0, 23)
                minutes_ago = random.randint(0, 59)
                created_at = timezone.now() - timedelta(
                    days=days_ago,
                    hours=hours_ago,
                    minutes=minutes_ago
                )

                # Generate patient demographics
                patient_id = f'PAT{random.randint(10000, 99999)}'
                patient_age = random.randint(18, 90)
                patient_sex = random.choice(patient_sexes)

                # Generate DICOM metadata
                modality = random.choice(modalities)
                body_part = random.choice(body_parts)

                # Select random model
                model = random.choice(models)

                # Determine status
                status = random.choices(statuses, weights=status_weights)[0]

                # Calculate timestamps based on status
                dispatched_at = created_at + timedelta(seconds=random.randint(1, 10))
                started_processing_at = None
                completed_at = None

                if status in ['PROCESSING', 'COMPLETED', 'FAILED']:
                    started_processing_at = dispatched_at + timedelta(seconds=random.randint(1, 30))

                    if status in ['COMPLETED', 'FAILED']:
                        # Completed or failed tasks have completion time
                        # processing_duration is calculated automatically from timestamps
                        duration_seconds = random.uniform(5.0, 300.0)  # 5s to 5min
                        completed_at = started_processing_at + timedelta(seconds=duration_seconds)

                # Create analysis task
                task = AnalysisTask.objects.create(
                    model=model,
                    input_image=medical_image,
                    created_by=user,
                    status=status,
                    parameters={
                        'modality': modality,
                        'body_part': body_part,
                        'patient_id': patient_id,
                        'patient_age': patient_age,
                        'patient_sex': patient_sex,
                    },
                    created_at=created_at,
                    dispatched_at=dispatched_at if status != 'PENDING' else None,
                    started_processing_at=started_processing_at,
                    completed_at=completed_at,
                    error_message='Simulated error' if status == 'FAILED' else '',
                    result_metadata={
                        'feature_count': random.randint(128, 2048),
                        'confidence': random.uniform(0.7, 0.99),
                    } if status == 'COMPLETED' else {},
                )

                tasks_created += 1

                # Progress indicator
                if (i + 1) % 10 == 0:
                    self.stdout.write(f'Progress: {i + 1}/{count} tasks created...')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating task {i}: {str(e)}'))
                continue

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Successfully generated {tasks_created} analysis tasks'
        ))

        # Status breakdown
        self.stdout.write('\nStatus Distribution:')
        for status in statuses:
            count_status = AnalysisTask.objects.filter(status=status).count()
            percentage = (count_status / tasks_created * 100) if tasks_created > 0 else 0
            self.stdout.write(f'  {status}: {count_status} ({percentage:.1f}%)')

        # Model breakdown
        self.stdout.write('\nModel Distribution:')
        for model in models:
            count_model = AnalysisTask.objects.filter(model=model).count()
            if count_model > 0:
                percentage = (count_model / tasks_created * 100) if tasks_created > 0 else 0
                self.stdout.write(f'  {model.name}: {count_model} ({percentage:.1f}%)')

        self.stdout.write(self.style.SUCCESS(
            f'\nDummy data generation complete! You can now test the Statistics page.\n'
        ))
