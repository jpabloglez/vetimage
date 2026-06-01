"""
Metadata Extractors for Multiple Medical Image Formats

Provides a unified interface for extracting metadata from DICOM, NIfTI, and standard image formats.
All extractors normalize metadata to a common schema for consistent processing.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import re
import logging

logger = logging.getLogger(__name__)


class BaseMetadataExtractor(ABC):
    """
    Abstract base class for medical image metadata extraction.

    All extractors must normalize metadata to a common schema that includes:
    - format: File format identifier
    - modality: Medical imaging modality (MR, CT, OCT, etc.)
    - dimensions: Image dimensions
    - Additional format-specific metadata
    """

    @abstractmethod
    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a medical image file.

        Args:
            file_path: Absolute path to the image file

        Returns:
            Dictionary with standardized metadata schema

        Raises:
            ValueError: If file cannot be parsed or is invalid
        """
        pass

    def _normalize_metadata(self, raw_metadata: Dict[str, Any], format_type: str) -> Dict[str, Any]:
        """
        Ensure metadata has required fields with sensible defaults.

        Args:
            raw_metadata: Raw extracted metadata
            format_type: Format identifier (dicom, nifti, image)

        Returns:
            Normalized metadata dictionary
        """
        normalized = {
            'format': format_type,
            'modality': raw_metadata.get('modality', 'UNKNOWN'),
            'dimensions': raw_metadata.get('dimensions', {}),
            'metadata': raw_metadata
        }
        return normalized


class DicomMetadataExtractor(BaseMetadataExtractor):
    """
    DICOM metadata extractor using pydicom.
    Reuses existing extract_all_dicom_tags utility.
    """

    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from DICOM file.

        Args:
            file_path: Path to DICOM file

        Returns:
            Normalized metadata with all DICOM tags
        """
        try:
            import pydicom
            from .utils import extract_all_dicom_tags

            # Read DICOM file
            dcm = pydicom.dcmread(file_path, force=True)

            # Extract all tags using existing utility
            all_tags = extract_all_dicom_tags(dcm, include_pixels=False)

            # Extract key metadata
            modality = str(dcm.get('Modality', 'UNKNOWN'))

            # Get dimensions
            dimensions = {
                'width': int(dcm.get('Columns', 0)),
                'height': int(dcm.get('Rows', 0)),
            }

            # Add depth for multi-frame images
            if hasattr(dcm, 'NumberOfFrames'):
                dimensions['depth'] = int(dcm.NumberOfFrames)

            # Extract anatomical region if available
            anatomical_region = None
            if hasattr(dcm, 'BodyPartExamined'):
                anatomical_region = str(dcm.BodyPartExamined).lower()

            # Build standardized metadata
            metadata = {
                'format': 'dicom',
                'modality': modality,
                'dimensions': dimensions,
                'anatomical_region': anatomical_region,
                'patient_position': str(dcm.get('PatientPosition', '')),
                'study_description': str(dcm.get('StudyDescription', '')),
                'series_description': str(dcm.get('SeriesDescription', '')),
                'acquisition_date': str(dcm.get('AcquisitionDate', '')),
                'all_tags': all_tags,
            }

            # Add voxel size if available
            if hasattr(dcm, 'PixelSpacing'):
                pixel_spacing = dcm.PixelSpacing
                voxel_size = {
                    'x': float(pixel_spacing[0]),
                    'y': float(pixel_spacing[1]),
                }
                if hasattr(dcm, 'SliceThickness'):
                    voxel_size['z'] = float(dcm.SliceThickness)
                metadata['voxel_size'] = voxel_size

            return metadata

        except Exception as e:
            logger.error(f"Failed to extract DICOM metadata from {file_path}: {e}")
            raise ValueError(f"Invalid DICOM file: {str(e)}")


class NiftiMetadataExtractor(BaseMetadataExtractor):
    """
    NIfTI metadata extractor using nibabel.
    """

    # Common modality patterns in NIfTI filenames
    MODALITY_PATTERNS = {
        r't1w?': 'MR',
        r't2w?': 'MR',
        r'flair': 'MR',
        r'dwi': 'MR',
        r'adc': 'MR',
        r'bold': 'MR',
        r'ct': 'CT',
        r'pet': 'PT',
        r'oct': 'OCT',
    }

    def _infer_modality_from_filename(self, filename: str) -> str:
        """
        Infer imaging modality from NIfTI filename patterns.

        Args:
            filename: Name of the NIfTI file

        Returns:
            Inferred modality or 'UNKNOWN'
        """
        filename_lower = filename.lower()

        for pattern, modality in self.MODALITY_PATTERNS.items():
            if re.search(pattern, filename_lower):
                return modality

        return 'UNKNOWN'

    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from NIfTI file.

        Args:
            file_path: Path to NIfTI file (.nii or .nii.gz)

        Returns:
            Normalized metadata with NIfTI header information
        """
        try:
            import nibabel as nib
            import numpy as np

            # Load NIfTI file
            img = nib.load(file_path)
            header = img.header

            # Get filename for modality inference
            filename = os.path.basename(file_path)
            modality = self._infer_modality_from_filename(filename)

            # Extract dimensions
            shape = img.shape
            dimensions = {
                'width': int(shape[0]),
                'height': int(shape[1]),
            }
            if len(shape) > 2:
                dimensions['depth'] = int(shape[2])
            if len(shape) > 3:
                dimensions['time_points'] = int(shape[3])

            # Extract voxel size (zooms)
            zooms = header.get_zooms()
            voxel_size = {
                'x': float(zooms[0]),
                'y': float(zooms[1]),
            }
            if len(zooms) > 2:
                voxel_size['z'] = float(zooms[2])

            # Get orientation
            try:
                orientation_codes = nib.aff2axcodes(img.affine)
                orientation = ''.join(orientation_codes)
            except Exception:
                orientation = 'UNKNOWN'

            # Extract description safely (handle both bytes and numpy array)
            descrip_raw = header.get('descrip', b'')
            try:
                # Convert numpy array to bytes if needed
                if hasattr(descrip_raw, 'tobytes'):
                    descrip_bytes = descrip_raw.tobytes()
                elif isinstance(descrip_raw, bytes):
                    descrip_bytes = descrip_raw
                else:
                    descrip_bytes = str(descrip_raw).encode('utf-8')
                # Decode and remove null bytes (PostgreSQL doesn't allow them)
                description = descrip_bytes.decode('utf-8', errors='ignore').replace('\x00', '').strip()
            except Exception:
                description = ''

            # Build metadata
            metadata = {
                'format': 'nifti',
                'modality': modality,
                'dimensions': dimensions,
                'voxel_size': voxel_size,
                'orientation': orientation,
                'data_type': str(header.get_data_dtype()),
                'qform_code': int(header['qform_code']) if 'qform_code' in header else None,
                'sform_code': int(header['sform_code']) if 'sform_code' in header else None,
                'description': description,
            }

            return metadata

        except ImportError:
            raise ValueError("nibabel is not installed. Install with: pip install nibabel")
        except Exception as e:
            logger.error(f"Failed to extract NIfTI metadata from {file_path}: {e}")
            raise ValueError(f"Invalid NIfTI file: {str(e)}")


class ImageMetadataExtractor(BaseMetadataExtractor):
    """
    Standard image format extractor (JPG, PNG) using Pillow.
    Extracts EXIF data if available, otherwise basic image properties.
    """

    def _extract_exif(self, img) -> Dict[str, Any]:
        """
        Extract EXIF metadata from image.

        Args:
            img: PIL Image object

        Returns:
            Dictionary with EXIF data
        """
        exif_data = {}

        try:
            from PIL.ExifTags import TAGS
            exif = img.getexif()

            if exif:
                for tag_id, value in exif.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    try:
                        # Convert bytes to string
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        exif_data[str(tag_name)] = str(value)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Failed to extract EXIF data: {e}")

        return exif_data

    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from standard image file (JPG, PNG).

        Args:
            file_path: Path to image file

        Returns:
            Normalized metadata with image properties
        """
        try:
            from PIL import Image

            # Open image
            img = Image.open(file_path)

            # Extract basic properties
            dimensions = {
                'width': img.width,
                'height': img.height,
            }

            # Extract EXIF if available
            exif_data = self._extract_exif(img)

            # Build metadata
            metadata = {
                'format': 'image',
                'modality': 'UNKNOWN',  # Requires user input
                'dimensions': dimensions,
                'color_mode': img.mode,
                'file_format': img.format,
                'exif': exif_data,
            }

            # Try to infer modality from EXIF
            if 'ImageDescription' in exif_data:
                description_lower = exif_data['ImageDescription'].lower()
                if 'xray' in description_lower or 'x-ray' in description_lower:
                    metadata['modality'] = 'CR'
                elif 'fundus' in description_lower or 'retina' in description_lower:
                    metadata['modality'] = 'OP'  # Ophthalmic Photography

            return metadata

        except Exception as e:
            logger.error(f"Failed to extract image metadata from {file_path}: {e}")
            raise ValueError(f"Invalid image file: {str(e)}")


class MetadataExtractorFactory:
    """
    Factory for creating appropriate metadata extractor based on file extension.
    """

    EXTRACTORS = {
        '.dcm': DicomMetadataExtractor,
        '.dicom': DicomMetadataExtractor,
        '.nii': NiftiMetadataExtractor,
        '.nii.gz': NiftiMetadataExtractor,
        '.jpg': ImageMetadataExtractor,
        '.jpeg': ImageMetadataExtractor,
        '.png': ImageMetadataExtractor,
    }

    @classmethod
    def get_extractor(cls, file_path: str) -> BaseMetadataExtractor:
        """
        Get appropriate metadata extractor for file.

        Args:
            file_path: Path to image file

        Returns:
            Metadata extractor instance

        Raises:
            ValueError: If file format is not supported
        """
        # Check for .nii.gz first (multi-part extension)
        if file_path.lower().endswith('.nii.gz'):
            return cls.EXTRACTORS['.nii.gz']()

        # Check single extension
        ext = os.path.splitext(file_path)[1].lower()

        if ext in cls.EXTRACTORS:
            return cls.EXTRACTORS[ext]()

        raise ValueError(f"Unsupported file format: {ext}")

    @classmethod
    def extract_metadata(cls, file_path: str) -> Dict[str, Any]:
        """
        Convenience method to extract metadata in one call.

        Args:
            file_path: Path to image file

        Returns:
            Normalized metadata dictionary
        """
        extractor = cls.get_extractor(file_path)
        return extractor.extract(file_path)
