"""
Format Conversion Service

Converts DICOM images to other formats (JPEG, PNG, NIfTI).
"""

import logging
import os
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import pydicom
from django.conf import settings

from dicom_images.models import MedicalImage, MedicalSeries, MedicalStudy
from dicom_images.utils import dicom_to_image

logger = logging.getLogger(__name__)


class FormatConversionService:
    """Converts DICOM files to JPEG, PNG, or NIfTI formats."""

    SUPPORTED_FORMATS = ('jpeg', 'png', 'nifti')

    def convert_dicom_to_image(self, image_id, fmt, user):
        """
        Convert a single DICOM image to JPEG or PNG.

        Returns a BytesIO buffer containing the image.
        """
        image = MedicalImage.objects.select_related(
            'series__study'
        ).get(id=image_id, series__study__uploaded_by=user)

        if fmt not in ('jpeg', 'png'):
            raise ValueError(f"Unsupported image format: {fmt}")

        dcm = pydicom.dcmread(image.file.path)
        buf = dicom_to_image(dcm, output_format=fmt.upper())
        return buf

    def convert_series_to_nifti(self, series_id, user):
        """
        Stack all DICOM slices in a series into a 3D NIfTI volume.

        Returns the path to the output .nii.gz file relative to MEDIA_ROOT.
        """
        import nibabel as nib
        import numpy as np

        series = MedicalSeries.objects.select_related('study').get(
            id=series_id, study__uploaded_by=user,
        )

        images = (
            MedicalImage.objects
            .filter(series=series)
            .order_by('instance_number')
        )

        slices = []
        for img in images:
            if not img.file or not os.path.isfile(img.file.path):
                continue
            try:
                dcm = pydicom.dcmread(img.file.path)
                slices.append(dcm.pixel_array)
            except Exception:
                logger.warning(f"Cannot read pixel data from image {img.id}")
                continue

        if not slices:
            raise ValueError("No valid DICOM slices found in the series.")

        volume = np.stack(slices, axis=-1)
        nii = nib.Nifti1Image(volume, affine=np.eye(4))

        output_dir = Path(settings.MEDIA_ROOT) / 'converted'
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"nifti_{uuid.uuid4().hex[:12]}.nii.gz"
        filepath = output_dir / filename
        nib.save(nii, str(filepath))

        return f"converted/{filename}"

    def batch_convert(self, study_id, target_format, user):
        """
        Convert all images in a study to the target format
        and package them into a ZIP file.

        Returns the path to the output ZIP relative to MEDIA_ROOT.
        """
        study = MedicalStudy.objects.get(id=study_id, uploaded_by=user)
        images = MedicalImage.objects.filter(
            series__study=study
        ).select_related('series')

        output_dir = Path(settings.MEDIA_ROOT) / 'converted'
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_name = f"convert_{uuid.uuid4().hex[:12]}.zip"
        zip_path = output_dir / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for img in images:
                if not img.file or not os.path.isfile(img.file.path):
                    continue
                try:
                    dcm = pydicom.dcmread(img.file.path)
                except Exception:
                    continue

                if target_format == 'nifti':
                    # NIfTI is handled at series level — skip per-image
                    continue

                try:
                    buf = dicom_to_image(dcm, output_format=target_format.upper())
                    ext = 'jpg' if target_format == 'jpeg' else target_format
                    arcname = (
                        f"{img.series.series_instance_uid}/"
                        f"{os.path.splitext(img.original_filename)[0]}.{ext}"
                    )
                    zf.writestr(arcname, buf.read())
                except Exception:
                    logger.warning(f"Conversion failed for image {img.id}")
                    continue

        return f"converted/{zip_name}"
