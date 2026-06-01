"""
Core Services

Shared business logic for data integrity, cleanup, and maintenance operations.
"""

import os
from datetime import timedelta
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.conf import settings


class DataIntegrityService:
    """
    Service for checking and fixing data integrity issues.
    """

    @staticmethod
    def check_orphaned_records():
        """
        Find records with invalid foreign key references.

        Returns:
            dict: Summary of orphaned records found
                {
                    'orphaned_series': int,    # Series with no study
                    'orphaned_images': int,    # Images with no series
                    'orphaned_annotations': int,  # Annotations with no image
                    'orphaned_profiles': int,  # UserProfiles with no user
                }
        """
        from dicom_images.models import MedicalSeries, MedicalImage, ImageAnnotation
        from users.models import UserProfile

        results = {
            'orphaned_series': 0,
            'orphaned_images': 0,
            'orphaned_annotations': 0,
            'orphaned_profiles': 0,
        }

        # Check for series without a study
        orphaned_series = MedicalSeries.objects.filter(study__isnull=True)
        results['orphaned_series'] = orphaned_series.count()

        # Check for images without a series
        orphaned_images = MedicalImage.objects.filter(series__isnull=True)
        results['orphaned_images'] = orphaned_images.count()

        # Check for annotations without an image
        orphaned_annotations = ImageAnnotation.objects.filter(image__isnull=True)
        results['orphaned_annotations'] = orphaned_annotations.count()

        # Check for user profiles without a user
        orphaned_profiles = UserProfile.objects.filter(user__isnull=True)
        results['orphaned_profiles'] = orphaned_profiles.count()

        return results

    @staticmethod
    def check_invalid_file_references():
        """
        Find database records referencing files that don't exist on disk.

        Returns:
            dict: Summary of invalid file references
                {
                    'missing_dicom_files': int,     # DICOM files missing
                    'missing_thumbnails': int,      # Thumbnail files missing
                    'invalid_file_paths': list,     # List of missing file paths
                }
        """
        from dicom_images.models import MedicalImage, MedicalSeries

        results = {
            'missing_dicom_files': 0,
            'missing_thumbnails': 0,
            'invalid_file_paths': [],
        }

        # Check DICOM files
        for image in MedicalImage.objects.all():
            if image.file:
                full_path = image.file.path
                if not os.path.exists(full_path):
                    results['missing_dicom_files'] += 1
                    results['invalid_file_paths'].append(full_path)

        # Check thumbnail files
        for series in MedicalSeries.objects.all():
            for thumbnail_field in ['thumbnail_small', 'thumbnail_medium', 'thumbnail_large']:
                thumbnail = getattr(series, thumbnail_field)
                if thumbnail:
                    try:
                        full_path = thumbnail.path
                        if not os.path.exists(full_path):
                            results['missing_thumbnails'] += 1
                            results['invalid_file_paths'].append(full_path)
                    except ValueError:
                        # Handle case where path is not available
                        pass

        return results

    @staticmethod
    def fix_orphaned_records(dry_run=False):
        """
        Delete orphaned records from the database.

        Args:
            dry_run: If True, don't actually delete (default: False)

        Returns:
            dict: Summary of deletions performed
                {
                    'deleted_series': int,
                    'deleted_images': int,
                    'deleted_annotations': int,
                    'deleted_profiles': int,
                }
        """
        from dicom_images.models import MedicalSeries, MedicalImage, ImageAnnotation
        from users.models import UserProfile

        results = {
            'deleted_series': 0,
            'deleted_images': 0,
            'deleted_annotations': 0,
            'deleted_profiles': 0,
        }

        if dry_run:
            # Just count what would be deleted
            results['deleted_series'] = MedicalSeries.objects.filter(study__isnull=True).count()
            results['deleted_images'] = MedicalImage.objects.filter(series__isnull=True).count()
            results['deleted_annotations'] = ImageAnnotation.objects.filter(image__isnull=True).count()
            results['deleted_profiles'] = UserProfile.objects.filter(user__isnull=True).count()
        else:
            # Actually delete orphaned records
            deleted_series, _ = MedicalSeries.objects.filter(study__isnull=True).delete()
            results['deleted_series'] = deleted_series

            deleted_images, _ = MedicalImage.objects.filter(series__isnull=True).delete()
            results['deleted_images'] = deleted_images

            deleted_annotations, _ = ImageAnnotation.objects.filter(image__isnull=True).delete()
            results['deleted_annotations'] = deleted_annotations

            deleted_profiles, _ = UserProfile.objects.filter(user__isnull=True).delete()
            results['deleted_profiles'] = deleted_profiles

        return results


class CleanupService:
    """
    Service for cleanup and maintenance operations.
    """

    @staticmethod
    def cleanup_old_sessions(days_old=30, dry_run=False):
        """
        Remove Django sessions older than specified days.

        Args:
            days_old: Age threshold in days (default: 30)
            dry_run: If True, don't actually delete (default: False)

        Returns:
            dict: Summary of cleanup operation
                {
                    'deleted_count': int,
                    'cutoff_date': datetime,
                }
        """
        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Find expired sessions
        expired_sessions = Session.objects.filter(expire_date__lt=cutoff_date)
        count = expired_sessions.count()

        if not dry_run:
            expired_sessions.delete()

        return {
            'deleted_count': count,
            'cutoff_date': cutoff_date,
        }

    @staticmethod
    def cleanup_blacklisted_tokens(dry_run=False):
        """
        Clean up expired JWT refresh tokens from blacklist.

        Args:
            dry_run: If True, don't actually delete (default: False)

        Returns:
            dict: Summary of cleanup operation
                {
                    'deleted_outstanding': int,  # Deleted outstanding tokens
                    'deleted_blacklisted': int,  # Deleted blacklisted tokens
                }
        """
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                OutstandingToken,
                BlacklistedToken
            )
        except ImportError:
            # Token blacklist not installed
            return {
                'deleted_outstanding': 0,
                'deleted_blacklisted': 0,
                'error': 'rest_framework_simplejwt.token_blacklist not installed'
            }

        results = {
            'deleted_outstanding': 0,
            'deleted_blacklisted': 0,
        }

        # Find expired outstanding tokens
        now = timezone.now()
        expired_outstanding = OutstandingToken.objects.filter(expires_at__lt=now)
        results['deleted_outstanding'] = expired_outstanding.count()

        if not dry_run:
            # Delete blacklisted entries for expired tokens first
            expired_token_ids = list(expired_outstanding.values_list('id', flat=True))
            deleted_blacklisted = BlacklistedToken.objects.filter(
                token_id__in=expired_token_ids
            ).delete()
            results['deleted_blacklisted'] = deleted_blacklisted[0] if deleted_blacklisted else 0

            # Then delete the outstanding tokens
            expired_outstanding.delete()

        return results
