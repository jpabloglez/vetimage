"""
Users Services

Business logic for user creation, management, and anonymization.
"""

from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from faker import Faker


class UserCreationService:
    """
    Service for creating users and demo data.
    """

    @staticmethod
    def create_superuser(email, password, **kwargs):
        """
        Create a superuser with UserProfile and Organization.

        Args:
            email: Superuser email
            password: Superuser password
            **kwargs: Additional fields for User model

        Returns:
            User: Created superuser instance
        """
        from users.models import User, UserProfile, Organization

        # Create superuser
        user = User.objects.create_superuser(
            email=email,
            password=password,
            role=5,  # Superuser role
            **kwargs
        )

        # Create organization for superuser
        org = Organization.objects.create(
            user=user,
            centre='Admin Organization',
            address='123 Admin St',
            city='Admin City',
            billing_address='123 Admin St',
            billing_code='ADMIN001'
        )

        # Create user profile
        UserProfile.objects.create(
            user=user,
            organization=org,
            first_name='Admin',
            last_name='User',
            email=email,
            phone='1234567890',
            address='123 Admin St',
            city='Admin City',
            state='Admin State',
            country='Admin Country',
            zip='12345'
        )

        return user

    @staticmethod
    def create_demo_users(count=3):
        """
        Create demo users with realistic data using Faker.

        Args:
            count: Number of demo users to create (default: 3)

        Returns:
            list: List of created User instances
        """
        from users.models import User, UserProfile, Organization
        from dicom_images.models import UserStorageQuota
        from django.conf import settings

        fake = Faker()
        created_users = []

        for i in range(count):
            # Generate unique email
            email = fake.unique.email()

            # Create user
            user = User.objects.create_user(
                email=email,
                password='demo123',  # Default demo password
                role=1  # Regular user role
            )

            # Create organization
            org = Organization.objects.create(
                user=user,
                centre=fake.company(),
                address=fake.street_address(),
                city=fake.city(),
                billing_address=fake.street_address(),
                billing_code=fake.bothify(text='ORG-####')
            )

            # Create user profile
            UserProfile.objects.create(
                user=user,
                organization=org,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=email,
                phone=fake.phone_number()[:12],  # Limit to 12 chars
                address=fake.street_address(),
                city=fake.city(),
                state=fake.state(),
                country=fake.country(),
                zip=fake.postcode()[:10],  # Limit to 10 chars
                language='en'
            )

            # Create storage quota
            UserStorageQuota.objects.create(
                user=user,
                used_bytes=0,
                quota_bytes=getattr(settings, 'USER_STORAGE_QUOTA', 5 * 1024 * 1024 * 1024)
            )

            created_users.append(user)

        return created_users


class AnonymizationService:
    """
    Service for GDPR-compliant user data anonymization.
    """

    @staticmethod
    @transaction.atomic
    def anonymize_user(user_id, keep_studies=False):
        """
        Anonymize a user's personal information.

        This operation:
        - Replaces email with anonymized_{user_id}@example.com
        - Sets user as inactive
        - Clears PII from UserProfile
        - Optionally deletes or anonymizes studies

        Args:
            user_id: ID of user to anonymize
            keep_studies: If True, keep studies but anonymize patient names (default: False)

        Returns:
            dict: Summary of anonymization operation
                {
                    'user_id': int,
                    'original_email': str,
                    'new_email': str,
                    'studies_deleted': int,
                    'studies_anonymized': int,
                }
        """
        from users.models import User, UserProfile
        from dicom_images.models import MedicalStudy

        # Get user
        user = User.objects.get(id=user_id)
        original_email = user.email

        # Anonymize user
        anonymized_email = f'anonymized_{user_id}@example.com'
        user.email = anonymized_email
        user.is_active = False
        user.save()

        # Anonymize or clear user profile
        try:
            profile = UserProfile.objects.get(user=user)
            profile.first_name = f'Anonymized'
            profile.last_name = f'User{user_id}'
            profile.email = anonymized_email
            profile.phone = ''
            profile.address = 'ANONYMIZED'
            profile.city = 'ANONYMIZED'
            profile.state = 'ANONYMIZED'
            profile.country = 'ANONYMIZED'
            profile.zip = ''
            if profile.image:
                profile.image.delete()
                profile.image = None
            profile.save()
        except UserProfile.DoesNotExist:
            pass

        # Handle studies
        studies_deleted = 0
        studies_anonymized = 0

        if keep_studies:
            # Anonymize patient data in studies
            studies = MedicalStudy.objects.filter(uploaded_by=user)
            for study in studies:
                study.patient_name = f'ANONYMIZED_{study.id}'
                study.patient_id = f'ANON{study.id}'
                study.save()
                studies_anonymized += 1
        else:
            # Delete all studies (cascades to series and images)
            studies = MedicalStudy.objects.filter(uploaded_by=user)
            studies_deleted = studies.count()
            studies.delete()

        return {
            'user_id': user_id,
            'original_email': original_email,
            'new_email': anonymized_email,
            'studies_deleted': studies_deleted,
            'studies_anonymized': studies_anonymized,
        }

    @staticmethod
    def anonymize_inactive_users(inactive_days, dry_run=False):
        """
        Bulk anonymize users who haven't logged in for specified days.

        Args:
            inactive_days: Number of days of inactivity threshold
            dry_run: If True, don't actually anonymize (default: False)

        Returns:
            dict: Summary of bulk anonymization
                {
                    'found_count': int,
                    'anonymized_count': int,
                    'user_ids': list,
                }
        """
        from users.models import User

        cutoff_date = timezone.now() - timedelta(days=inactive_days)

        # Find inactive users (excluding superusers)
        inactive_users = User.objects.filter(
            last_login__lt=cutoff_date,
            is_active=True,
            is_superuser=False
        )

        found_count = inactive_users.count()
        user_ids = list(inactive_users.values_list('id', flat=True))

        anonymized_count = 0
        if not dry_run:
            for user_id in user_ids:
                try:
                    AnonymizationService.anonymize_user(
                        user_id=user_id,
                        keep_studies=False
                    )
                    anonymized_count += 1
                except Exception as e:
                    # Log error but continue with other users
                    print(f"Failed to anonymize user {user_id}: {e}")

        return {
            'found_count': found_count,
            'anonymized_count': anonymized_count if not dry_run else 0,
            'user_ids': user_ids,
        }
