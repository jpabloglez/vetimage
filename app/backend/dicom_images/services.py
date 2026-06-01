"""
DICOM Images Services

Business logic for DICOM data generation, storage verification, and validation.
"""

import os
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from faker import Faker


class DicomDataGenerationService:
    """
    Service for generating test DICOM data.

    Note: This creates database records with realistic metadata but does NOT
    create actual DICOM files. Useful for testing the database schema and API.
    """

    @staticmethod
    @transaction.atomic
    def generate_study(user, modality='CT', num_series=3, num_images_per_series=10):
        """
        Generate a complete DICOM study with series and images.

        Args:
            user: User instance who owns the study
            modality: Imaging modality (CT, MR, CR, etc.)
            num_series: Number of series to create
            num_images_per_series: Number of images per series

        Returns:
            MedicalStudy: The created study instance
        """
        from dicom_images.models import MedicalStudy, MedicalSeries, MedicalImage, UserStorageQuota

        fake = Faker()

        # Generate study
        study_date = fake.date_between(start_date='-2y', end_date='today')
        # Generate a time object (not string) for use with datetime.combine()
        import datetime as dt
        study_time = dt.time(
            hour=fake.random_int(min=0, max=23),
            minute=fake.random_int(min=0, max=59),
            second=fake.random_int(min=0, max=59)
        )

        study = MedicalStudy.objects.create(
            study_instance_uid=f"1.2.840.{fake.random_int(min=100000, max=999999)}.{fake.random_int(min=1000, max=9999)}",
            patient_id=fake.bothify(text='PAT####'),
            patient_name=f"{fake.last_name().upper()}^{fake.first_name().upper()}",
            patient_birth_date=fake.date_of_birth(minimum_age=18, maximum_age=90),
            patient_sex=fake.random_element(elements=('M', 'F')),
            study_date=study_date,
            study_time=study_time,
            study_description=DicomDataGenerationService._get_study_description(modality),
            accession_number=fake.bothify(text='ACC######'),
            uploaded_by=user,
            total_size_bytes=0,
            patient_name_normalized=f"{fake.last_name()} {fake.first_name()}".lower(),
            study_description_normalized=DicomDataGenerationService._get_study_description(modality).lower(),
        )

        total_bytes = 0

        # Generate series
        for series_num in range(1, num_series + 1):
            series = MedicalSeries.objects.create(
                study=study,
                series_instance_uid=f"{study.study_instance_uid}.{series_num}",
                series_number=series_num,
                series_description=DicomDataGenerationService._get_series_description(modality, series_num),
                modality=modality,
                body_part_examined=DicomDataGenerationService._get_body_part(modality),
                protocol_name=DicomDataGenerationService._get_protocol_name(modality),
                series_date=study_date,
                series_time=study_time,
                series_description_normalized=DicomDataGenerationService._get_series_description(modality, series_num).lower(),
            )

            # Generate images for this series
            for instance_num in range(1, num_images_per_series + 1):
                # Generate fake file size (typical DICOM slice: 512x512 = ~500KB)
                file_size = fake.random_int(min=400000, max=600000)
                total_bytes += file_size

                sop_uid = f"{series.series_instance_uid}.{instance_num}"

                # Note: We're NOT creating actual files, just database records
                MedicalImage.objects.create(
                    series=series,
                    sop_instance_uid=sop_uid,
                    sop_class_uid="1.2.840.10008.5.1.4.1.1.2",  # CT Image Storage
                    instance_number=instance_num,
                    file_size_bytes=file_size,
                    original_filename=f"CT{instance_num:04d}.dcm",
                    rows=512,
                    columns=512,
                    number_of_frames=1,
                    acquisition_datetime=timezone.make_aware(
                        datetime.combine(study_date, study_time)
                    ),
                    pixel_spacing_row=0.5,
                    pixel_spacing_column=0.5,
                    slice_thickness=2.5,
                    slice_location=float(instance_num * 2.5),
                    window_center=40,
                    window_width=400,
                    min_pixel_value=-1024,
                    max_pixel_value=3071,
                )

        # Update study total size
        study.total_size_bytes = total_bytes
        study.save()

        # Update user storage quota
        quota, created = UserStorageQuota.objects.get_or_create(
            user=user,
            defaults={'used_bytes': 0, 'quota_bytes': 5 * 1024 * 1024 * 1024}
        )
        quota.used_bytes += total_bytes
        quota.save()

        return study

    @staticmethod
    def _get_study_description(modality):
        """Get realistic study description based on modality"""
        descriptions = {
            'CT': ['CT CHEST W/O CONTRAST', 'CT HEAD W/O CONTRAST', 'CT ABDOMEN/PELVIS W CONTRAST'],
            'MR': ['MRI BRAIN W/O CONTRAST', 'MRI SPINE W CONTRAST', 'MRI KNEE LEFT'],
            'CR': ['CHEST PA AND LATERAL', 'ABDOMEN SUPINE', 'PELVIS AP'],
            'DX': ['CHEST 1 VIEW', 'HAND 2 VIEWS', 'FOOT AP/LATERAL'],
        }
        fake = Faker()
        return fake.random_element(descriptions.get(modality, descriptions['CT']))

    @staticmethod
    def _get_series_description(modality, series_num):
        """Get realistic series description"""
        if modality == 'CT':
            return ['Axial', 'Coronal', 'Sagittal'][series_num % 3]
        elif modality == 'MR':
            return ['T1', 'T2', 'FLAIR'][series_num % 3]
        else:
            return f'Series {series_num}'

    @staticmethod
    def _get_body_part(modality):
        """Get realistic body part based on modality"""
        parts = {
            'CT': ['CHEST', 'HEAD', 'ABDOMEN', 'PELVIS'],
            'MR': ['BRAIN', 'SPINE', 'KNEE', 'SHOULDER'],
            'CR': ['CHEST', 'ABDOMEN', 'PELVIS'],
            'DX': ['CHEST', 'HAND', 'FOOT'],
        }
        fake = Faker()
        return fake.random_element(parts.get(modality, parts['CT']))

    @staticmethod
    def _get_protocol_name(modality):
        """Get realistic protocol name"""
        protocols = {
            'CT': ['Standard Chest', 'Head Non-Contrast', 'Abdomen Portal Venous'],
            'MR': ['Brain Standard', 'Spine Routine', 'Joint Standard'],
            'CR': ['Standard Radiography', 'Two View', 'Single View'],
        }
        fake = Faker()
        return fake.random_element(protocols.get(modality, protocols['CT']))


class StorageVerificationService:
    """
    Service for verifying and fixing storage quota discrepancies.
    """

    @staticmethod
    def verify_user_quota(user):
        """
        Verify that a user's reported storage matches actual usage.

        Args:
            user: User instance to verify

        Returns:
            dict: Verification result
                {
                    'user': User,
                    'user_email': str,
                    'reported_bytes': int,  # What's in UserStorageQuota
                    'actual_bytes': int,    # Sum of all file sizes
                    'difference': int,      # Difference (reported - actual)
                    'matches': bool,        # True if they match
                }
        """
        from dicom_images.models import MedicalImage, UserStorageQuota

        # Get reported usage from quota
        try:
            quota = UserStorageQuota.objects.get(user=user)
            reported_bytes = quota.used_bytes
        except UserStorageQuota.DoesNotExist:
            reported_bytes = 0

        # Calculate actual usage
        actual_bytes = MedicalImage.objects.filter(
            series__study__uploaded_by=user
        ).aggregate(
            total=Sum('file_size_bytes')
        )['total'] or 0

        difference = reported_bytes - actual_bytes

        return {
            'user': user,
            'user_email': user.email,
            'reported_bytes': reported_bytes,
            'actual_bytes': actual_bytes,
            'difference': difference,
            'matches': difference == 0,
        }

    @staticmethod
    def verify_all_quotas():
        """
        Verify storage quotas for all users.

        Returns:
            list: List of verification results for users with discrepancies
        """
        from users.models import User

        results = []
        users = User.objects.all()

        for user in users:
            result = StorageVerificationService.verify_user_quota(user)
            if not result['matches']:
                results.append(result)

        return results

    @staticmethod
    @transaction.atomic
    def fix_user_quota(user, dry_run=False):
        """
        Recalculate and update a user's storage quota.

        Args:
            user: User instance to fix
            dry_run: If True, don't actually update (default: False)

        Returns:
            dict: Fix result
                {
                    'user_email': str,
                    'old_bytes': int,
                    'new_bytes': int,
                    'updated': bool,
                }
        """
        from dicom_images.models import MedicalImage, UserStorageQuota

        # Calculate correct usage
        actual_bytes = MedicalImage.objects.filter(
            series__study__uploaded_by=user
        ).aggregate(
            total=Sum('file_size_bytes')
        )['total'] or 0

        # Get or create quota
        quota, created = UserStorageQuota.objects.get_or_create(
            user=user,
            defaults={'used_bytes': 0, 'quota_bytes': 5 * 1024 * 1024 * 1024}
        )

        old_bytes = quota.used_bytes

        if not dry_run:
            quota.used_bytes = actual_bytes
            quota.save()

        return {
            'user_email': user.email,
            'old_bytes': old_bytes,
            'new_bytes': actual_bytes,
            'updated': not dry_run,
        }


class DicomMetadataValidationService:
    """
    Service for validating DICOM file integrity and metadata.
    """

    @staticmethod
    def validate_dicom_file(image):
        """
        Validate a single DICOM image record.

        Checks:
        - File exists on disk
        - File is readable by pydicom (if exists)
        - SOP Instance UID matches database
        - Dimensions match database
        - Required DICOM tags present

        Args:
            image: MedicalImage instance to validate

        Returns:
            dict: Validation result
                {
                    'image_id': int,
                    'sop_uid': str,
                    'file_path': str,
                    'valid': bool,
                    'errors': list,  # List of error messages
                }
        """
        errors = []

        result = {
            'image_id': image.id,
            'sop_uid': image.sop_instance_uid,
            'file_path': str(image.file) if image.file else None,
            'valid': True,
            'errors': [],
        }

        # Check if file field is set
        if not image.file:
            errors.append("No file associated with this image record")
            result['valid'] = False
            result['errors'] = errors
            return result

        # Check if file exists on disk
        try:
            file_path = image.file.path
        except ValueError as e:
            errors.append(f"Invalid file path: {e}")
            result['valid'] = False
            result['errors'] = errors
            return result

        if not os.path.exists(file_path):
            errors.append("File does not exist on disk")
            result['valid'] = False

        # Try to read with pydicom (only if file exists)
        if os.path.exists(file_path):
            try:
                import pydicom
                ds = pydicom.dcmread(file_path, stop_before_pixels=True)

                # Validate SOP Instance UID
                if hasattr(ds, 'SOPInstanceUID'):
                    if ds.SOPInstanceUID != image.sop_instance_uid:
                        errors.append(
                            f"SOP Instance UID mismatch: "
                            f"DB={image.sop_instance_uid}, File={ds.SOPInstanceUID}"
                        )
                        result['valid'] = False
                else:
                    errors.append("Missing SOPInstanceUID tag in file")
                    result['valid'] = False

                # Validate dimensions
                if hasattr(ds, 'Rows') and hasattr(ds, 'Columns'):
                    if image.rows and ds.Rows != image.rows:
                        errors.append(f"Rows mismatch: DB={image.rows}, File={ds.Rows}")
                        result['valid'] = False
                    if image.columns and ds.Columns != image.columns:
                        errors.append(f"Columns mismatch: DB={image.columns}, File={ds.Columns}")
                        result['valid'] = False

                # Check for required tags
                required_tags = ['PatientID', 'StudyInstanceUID', 'SeriesInstanceUID']
                for tag in required_tags:
                    if not hasattr(ds, tag):
                        errors.append(f"Missing required tag: {tag}")
                        result['valid'] = False

            except Exception as e:
                errors.append(f"Failed to read DICOM file: {str(e)}")
                result['valid'] = False

        result['errors'] = errors
        return result

    @staticmethod
    def validate_all_dicom_files(limit=None):
        """
        Validate all DICOM files in the database.

        Args:
            limit: Maximum number of files to check (None = all)

        Returns:
            dict: Validation summary
                {
                    'total_checked': int,
                    'valid_count': int,
                    'invalid_count': int,
                    'invalid_images': list,  # List of invalid image results
                }
        """
        from dicom_images.models import MedicalImage

        images = MedicalImage.objects.all()
        if limit:
            images = images[:limit]

        total_checked = 0
        valid_count = 0
        invalid_count = 0
        invalid_images = []

        for image in images:
            result = DicomMetadataValidationService.validate_dicom_file(image)
            total_checked += 1

            if result['valid']:
                valid_count += 1
            else:
                invalid_count += 1
                invalid_images.append(result)

        return {
            'total_checked': total_checked,
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'invalid_images': invalid_images,
        }
