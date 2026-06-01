"""
DICOM Anonymization Service

Provides batch PHI removal for research datasets following DICOM PS3.15
Table E.1-1 (Attribute Confidentiality Profiles).

Three anonymization profiles:
  - basic: Remove critical identifiers (PatientName, PatientID, etc.)
  - full: Remove ~30 PHI tags per DICOM PS3.15
  - research: Full + UID replacement + consistent date shifting
"""

import hashlib
import os
import uuid
import zipfile
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import pydicom
from django.conf import settings
from django.utils import timezone


# -------------------------------------------------------------------------
# PHI Tag Definitions
# -------------------------------------------------------------------------

# Basic profile: critical direct identifiers
BASIC_PHI_TAGS = [
    (0x0010, 0x0010),  # PatientName
    (0x0010, 0x0020),  # PatientID
    (0x0010, 0x0030),  # PatientBirthDate
    (0x0010, 0x1001),  # OtherPatientNames
    (0x0008, 0x0090),  # ReferringPhysicianName
    (0x0008, 0x1050),  # PerformingPhysicianName
    (0x0008, 0x0080),  # InstitutionName
]

# Full profile: comprehensive PHI removal per PS3.15 E.1-1
FULL_PHI_TAGS = BASIC_PHI_TAGS + [
    (0x0010, 0x0040),  # PatientSex
    (0x0010, 0x1010),  # PatientAge
    (0x0010, 0x1020),  # PatientSize
    (0x0010, 0x1030),  # PatientWeight
    (0x0010, 0x21B0),  # AdditionalPatientHistory
    (0x0010, 0x2160),  # EthnicGroup
    (0x0010, 0x2180),  # Occupation
    (0x0010, 0x4000),  # PatientComments
    (0x0008, 0x0050),  # AccessionNumber
    (0x0008, 0x0081),  # InstitutionAddress
    (0x0008, 0x0092),  # ReferringPhysicianAddress
    (0x0008, 0x0094),  # ReferringPhysicianTelephoneNumbers
    (0x0008, 0x1048),  # PhysiciansOfRecord
    (0x0008, 0x1060),  # NameOfPhysiciansReadingStudy
    (0x0008, 0x1070),  # OperatorsName
    (0x0020, 0x4000),  # ImageComments
    (0x0032, 0x1032),  # RequestingPhysician
    (0x0032, 0x1060),  # RequestedProcedureDescription
    (0x0040, 0x0006),  # ScheduledPerformingPhysicianName
    (0x0040, 0x0244),  # PerformedProcedureStepStartDate
    (0x0040, 0x0253),  # PerformedProcedureStepID
    (0x0040, 0x1001),  # RequestedProcedureID
    (0x0040, 0xA730),  # ContentSequence (SR documents may contain PHI)
]


class AnonymizationProfile:
    """Defines which tags to remove/replace for each profile level."""

    BASIC = 'basic'
    FULL = 'full'
    RESEARCH = 'research'

    VALID_PROFILES = [BASIC, FULL, RESEARCH]

    @classmethod
    def get_tags(cls, profile):
        if profile == cls.BASIC:
            return BASIC_PHI_TAGS
        elif profile in (cls.FULL, cls.RESEARCH):
            return FULL_PHI_TAGS
        raise ValueError(f"Unknown profile: {profile}")


class AnonymizationService:
    """Anonymize DICOM datasets and produce downloadable ZIP archives."""

    def anonymize_dataset(self, dcm, profile='basic', prefix='ANON'):
        """
        Anonymize a pydicom Dataset in-memory.

        Args:
            dcm: pydicom.Dataset
            profile: 'basic', 'full', or 'research'
            prefix: Prefix for replacement values

        Returns:
            The modified Dataset (same object).
        """
        tags = AnonymizationProfile.get_tags(profile)

        for tag in tags:
            if tag in dcm:
                del dcm[tag]

        # Replace critical identifiers with anonymized values
        dcm.PatientName = f"{prefix}_PATIENT"
        dcm.PatientID = f"{prefix}_{uuid.uuid4().hex[:8].upper()}"

        if profile == AnonymizationProfile.RESEARCH:
            self._apply_research_transforms(dcm, prefix)

        return dcm

    def anonymize_study(self, study_id, profile, user):
        """
        Anonymize all images in a study and return a ZIP path.

        Args:
            study_id: MedicalStudy PK
            profile: Anonymization profile name
            user: User performing the operation

        Returns:
            str: Path to the output ZIP file relative to MEDIA_ROOT.
        """
        from dicom_images.models import MedicalImage, MedicalStudy

        study = MedicalStudy.objects.get(id=study_id, uploaded_by=user)
        images = MedicalImage.objects.filter(
            series__study=study
        ).select_related('series')

        return self._anonymize_to_zip(images, profile, prefix=f"STUDY_{study.id}")

    def anonymize_images(self, image_ids, profile, user):
        """
        Anonymize a list of specific images and return a ZIP path.

        Args:
            image_ids: List of MedicalImage PKs
            profile: Anonymization profile name
            user: User performing the operation

        Returns:
            str: Path to the output ZIP file relative to MEDIA_ROOT.
        """
        from dicom_images.models import MedicalImage

        images = MedicalImage.objects.filter(
            id__in=image_ids,
            series__study__uploaded_by=user,
        ).select_related('series')

        return self._anonymize_to_zip(images, profile, prefix='BATCH')

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _anonymize_to_zip(self, images, profile, prefix='ANON'):
        """Anonymize a queryset of images and write them to a ZIP file."""
        output_dir = Path(settings.MEDIA_ROOT) / 'anonymized'
        output_dir.mkdir(parents=True, exist_ok=True)

        zip_name = f"anon_{uuid.uuid4().hex[:12]}.zip"
        zip_path = output_dir / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for img in images:
                if not img.file or not os.path.isfile(img.file.path):
                    continue

                try:
                    dcm = pydicom.dcmread(img.file.path)
                except Exception:
                    continue

                self.anonymize_dataset(dcm, profile=profile, prefix=prefix)

                buf = BytesIO()
                dcm.save_as(buf)
                buf.seek(0)

                arcname = f"{img.series.series_instance_uid}/{img.original_filename}"
                zf.writestr(arcname, buf.read())

        # Return path relative to MEDIA_ROOT
        return f"anonymized/{zip_name}"

    def _apply_research_transforms(self, dcm, prefix):
        """Apply research-grade transforms: UID replacement + date shifting."""
        # UID replacement (deterministic based on original UID)
        for tag_name in ('StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'):
            if hasattr(dcm, tag_name):
                original_uid = getattr(dcm, tag_name)
                new_uid = self._generate_research_uid(original_uid, prefix)
                setattr(dcm, tag_name, new_uid)

        # Date shifting: shift all dates by a consistent offset
        shift = self._get_date_shift(prefix)
        for tag_name in ('StudyDate', 'SeriesDate', 'ContentDate', 'AcquisitionDate'):
            if hasattr(dcm, tag_name):
                original = getattr(dcm, tag_name)
                if original:
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(original, '%Y%m%d')
                        shifted = dt + shift
                        setattr(dcm, tag_name, shifted.strftime('%Y%m%d'))
                    except (ValueError, TypeError):
                        pass

    @staticmethod
    def _generate_research_uid(original_uid, prefix):
        """Generate a deterministic UID from the original (reproducible per study)."""
        seed = f"{prefix}:{original_uid}"
        digest = hashlib.sha256(seed.encode()).hexdigest()
        # Build a valid DICOM UID (max 64 chars, numeric with dots)
        uid_root = '2.25.'
        numeric = str(int(digest[:30], 16))
        return uid_root + numeric[:60]

    @staticmethod
    def _get_date_shift(prefix):
        """Return a consistent date shift for the given prefix."""
        digest = hashlib.sha256(prefix.encode()).hexdigest()
        days = (int(digest[:4], 16) % 365) + 30  # 30-394 day shift
        return timedelta(days=-days)
