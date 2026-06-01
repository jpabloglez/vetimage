"""
DICOM Image Processing Utilities

Functions for converting DICOM pixel data to web-compatible image formats
with proper windowing, modality LUT, and image transformations.
"""

import numpy as np
import pydicom
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional


# Default window/level presets for common modalities
WINDOW_PRESETS = {
    'CT': {
        'Lung': {'center': -600, 'width': 1500},
        'Mediastinum': {'center': 50, 'width': 350},
        'Bone': {'center': 300, 'width': 1500},
        'Brain': {'center': 40, 'width': 80},
        'Liver': {'center': 60, 'width': 160},
        'Abdomen': {'center': 40, 'width': 400},
    },
    'MR': {
        'Brain': {'center': 600, 'width': 1200},
        'Spine': {'center': 400, 'width': 800},
    },
    'CR': {
        'Chest': {'center': 32768, 'width': 65536},
    },
    'DX': {
        'Standard': {'center': 2048, 'width': 4096},
    },
}


def get_pixel_array(dcm: pydicom.Dataset) -> np.ndarray:
    """
    Extract pixel array from DICOM dataset with proper transformations.

    Args:
        dcm: pydicom Dataset object

    Returns:
        numpy array with pixel data
    """
    try:
        # Get pixel array
        pixel_array = dcm.pixel_array

        # Apply rescale slope and intercept (for CT Hounsfield units, etc.)
        if hasattr(dcm, 'RescaleSlope') and hasattr(dcm, 'RescaleIntercept'):
            slope = float(dcm.RescaleSlope)
            intercept = float(dcm.RescaleIntercept)
            pixel_array = pixel_array * slope + intercept

        return pixel_array
    except Exception as e:
        raise ValueError(f"Failed to extract pixel array: {str(e)}")


def apply_modality_lut(pixel_array: np.ndarray, dcm: pydicom.Dataset) -> np.ndarray:
    """
    Apply modality LUT transformation (Rescale Slope/Intercept).

    Args:
        pixel_array: Raw pixel data
        dcm: DICOM dataset with modality LUT information

    Returns:
        Transformed pixel array
    """
    if hasattr(dcm, 'RescaleSlope') and hasattr(dcm, 'RescaleIntercept'):
        slope = float(dcm.RescaleSlope)
        intercept = float(dcm.RescaleIntercept)
        return pixel_array * slope + intercept
    return pixel_array


def apply_windowing(
    pixel_array: np.ndarray,
    window_center: float,
    window_width: float
) -> np.ndarray:
    """
    Apply window/level (contrast) adjustment to pixel array.

    Args:
        pixel_array: Input pixel data
        window_center: Window center (level)
        window_width: Window width

    Returns:
        Windowed pixel array normalized to 0-255
    """
    # Calculate window boundaries
    lower = window_center - window_width / 2
    upper = window_center + window_width / 2

    # Apply windowing
    windowed = np.clip(pixel_array, lower, upper)

    # Normalize to 0-255
    if window_width != 0:
        windowed = ((windowed - lower) / window_width * 255).astype(np.uint8)
    else:
        windowed = np.zeros_like(pixel_array, dtype=np.uint8)

    return windowed


def get_default_window(dcm: pydicom.Dataset) -> Tuple[float, float]:
    """
    Get default window center and width from DICOM metadata or presets.

    Args:
        dcm: DICOM dataset

    Returns:
        Tuple of (window_center, window_width)
    """
    # Try to get from DICOM tags
    if hasattr(dcm, 'WindowCenter') and hasattr(dcm, 'WindowWidth'):
        # Handle multiple window values (take first)
        center = dcm.WindowCenter
        width = dcm.WindowWidth

        if isinstance(center, (list, tuple)):
            center = float(center[0])
        else:
            center = float(center)

        if isinstance(width, (list, tuple)):
            width = float(width[0])
        else:
            width = float(width)

        return center, width

    # Fall back to presets based on modality
    modality = getattr(dcm, 'Modality', 'CT')

    if modality in WINDOW_PRESETS:
        # Use first preset for modality
        preset_name = list(WINDOW_PRESETS[modality].keys())[0]
        preset = WINDOW_PRESETS[modality][preset_name]
        return preset['center'], preset['width']

    # Ultimate fallback: use full dynamic range
    pixel_array = get_pixel_array(dcm)
    center = float(np.mean(pixel_array))
    width = float(np.max(pixel_array) - np.min(pixel_array))
    return center, width


def get_window_preset(modality: str, preset_name: str) -> Optional[dict]:
    """
    Get window preset for specific modality.

    Args:
        modality: DICOM modality (CT, MR, etc.)
        preset_name: Name of preset (Lung, Brain, etc.)

    Returns:
        Dict with 'center' and 'width' or None if not found
    """
    if modality in WINDOW_PRESETS:
        return WINDOW_PRESETS[modality].get(preset_name)
    return None


def apply_voi_lut(pixel_array: np.ndarray, dcm: pydicom.Dataset) -> np.ndarray:
    """
    Apply VOI (Value of Interest) LUT transformation.

    Args:
        pixel_array: Input pixel data
        dcm: DICOM dataset

    Returns:
        Transformed pixel array
    """
    # For now, just apply window/level if available
    center, width = get_default_window(dcm)
    return apply_windowing(pixel_array, center, width)


def handle_photometric_interpretation(
    pixel_array: np.ndarray,
    dcm: pydicom.Dataset
) -> np.ndarray:
    """
    Handle photometric interpretation (inversion for MONOCHROME1).

    Args:
        pixel_array: Input pixel data (should be 0-255)
        dcm: DICOM dataset

    Returns:
        Corrected pixel array
    """
    photometric = getattr(dcm, 'PhotometricInterpretation', 'MONOCHROME2')

    # MONOCHROME1 means minimum value is white, maximum is black
    # Need to invert for display
    if photometric == 'MONOCHROME1':
        return 255 - pixel_array

    return pixel_array


def extract_frame(
    dcm: pydicom.Dataset,
    frame_number: int = 0
) -> np.ndarray:
    """
    Extract specific frame from multi-frame DICOM.

    Args:
        dcm: DICOM dataset
        frame_number: Frame index (0-based)

    Returns:
        Pixel array for specified frame
    """
    pixel_array = dcm.pixel_array

    # Check if multi-frame
    if len(pixel_array.shape) > 2:
        # Multi-frame image
        num_frames = pixel_array.shape[0]
        if frame_number >= num_frames:
            raise ValueError(f"Frame {frame_number} out of range (0-{num_frames-1})")
        return pixel_array[frame_number]
    else:
        # Single frame
        if frame_number != 0:
            raise ValueError(f"Single-frame image, frame must be 0")
        return pixel_array


def dicom_to_image(
    dcm: pydicom.Dataset,
    frame_number: int = 0,
    window_center: Optional[float] = None,
    window_width: Optional[float] = None,
    output_format: str = 'JPEG'
) -> BytesIO:
    """
    Convert DICOM dataset to web-compatible image format.

    Args:
        dcm: pydicom Dataset
        frame_number: Frame index for multi-frame images (default: 0)
        window_center: Window center for windowing (default: auto)
        window_width: Window width for windowing (default: auto)
        output_format: Output image format ('JPEG' or 'PNG')

    Returns:
        BytesIO buffer containing image data
    """
    try:
        # Extract frame
        pixel_array = extract_frame(dcm, frame_number)

        # Apply modality LUT (rescale slope/intercept)
        pixel_array = apply_modality_lut(pixel_array, dcm)

        # Get window parameters
        if window_center is None or window_width is None:
            default_center, default_width = get_default_window(dcm)
            window_center = window_center or default_center
            window_width = window_width or default_width

        # Apply windowing
        windowed_array = apply_windowing(pixel_array, window_center, window_width)

        # Handle photometric interpretation
        windowed_array = handle_photometric_interpretation(windowed_array, dcm)

        # Handle color images
        if len(windowed_array.shape) == 3:
            # RGB image
            pil_image = Image.fromarray(windowed_array, mode='RGB')
        else:
            # Grayscale image
            pil_image = Image.fromarray(windowed_array, mode='L')

        # Convert to output format
        output_buffer = BytesIO()

        if output_format.upper() == 'JPEG':
            pil_image.save(output_buffer, format='JPEG', quality=90, optimize=True)
        elif output_format.upper() == 'PNG':
            pil_image.save(output_buffer, format='PNG', optimize=True)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        output_buffer.seek(0)
        return output_buffer

    except Exception as e:
        raise ValueError(f"Failed to convert DICOM to image: {str(e)}")


def get_num_frames(dcm: pydicom.Dataset) -> int:
    """
    Get number of frames in DICOM dataset.

    Args:
        dcm: DICOM dataset

    Returns:
        Number of frames
    """
    if hasattr(dcm, 'NumberOfFrames'):
        return int(dcm.NumberOfFrames)

    pixel_array = dcm.pixel_array
    if len(pixel_array.shape) > 2:
        return pixel_array.shape[0]

    return 1


def get_image_dimensions(dcm: pydicom.Dataset) -> Tuple[int, int]:
    """
    Get image dimensions (width, height).

    Args:
        dcm: DICOM dataset

    Returns:
        Tuple of (width, height)
    """
    if hasattr(dcm, 'Columns') and hasattr(dcm, 'Rows'):
        return int(dcm.Columns), int(dcm.Rows)

    pixel_array = dcm.pixel_array
    if len(pixel_array.shape) >= 2:
        # Last two dimensions are height, width
        height, width = pixel_array.shape[-2:]
        return width, height

    raise ValueError("Cannot determine image dimensions")


# ============================================================================
# DICOM Tag Extraction Utilities
# ============================================================================

def extract_all_dicom_tags(dcm: pydicom.Dataset, include_pixels: bool = False) -> dict:
    """
    Extract ALL DICOM tags to JSON-serializable dictionary.

    Args:
        dcm: pydicom Dataset object
        include_pixels: Whether to include pixel data (default: False)

    Returns:
        Dictionary with all DICOM tags in format {tag_hex: {vr, name, value}}
    """
    import logging
    logger = logging.getLogger(__name__)

    tags_dict = {}

    for elem in dcm:
        # Skip pixel data if requested
        if not include_pixels and elem.tag == 0x7FE00010:
            continue

        # Format tag as hex string (e.g., "00100020")
        tag_key = f"{elem.tag.group:04X}{elem.tag.element:04X}"

        try:
            if elem.VR == 'SQ':  # Sequence
                # Recursively process sequences
                sequence_items = []
                for item in elem.value:
                    sequence_items.append(extract_all_dicom_tags(item, include_pixels))

                tags_dict[tag_key] = {
                    'vr': elem.VR,
                    'name': elem.name,
                    'value': sequence_items
                }
            else:
                # Convert value to JSON-serializable format
                if elem.VM > 1:  # Multiple values
                    value = [str(v) for v in elem.value]
                else:
                    value = str(elem.value)

                tags_dict[tag_key] = {
                    'vr': elem.VR,
                    'name': elem.name,
                    'value': value
                }
        except Exception as e:
            logger.warning(f"Failed to serialize tag {tag_key} ({elem.name}): {e}")
            # Store error information
            tags_dict[tag_key] = {
                'vr': elem.VR,
                'name': elem.name,
                'value': None,
                'error': str(e)
            }

    return tags_dict


def normalize_text_for_search(text: str) -> str:
    """
    Normalize text for full-text search (case-insensitive, remove special chars).

    Args:
        text: Input text to normalize

    Returns:
        Normalized text (lowercase, alphanumeric + spaces only)
    """
    import re

    if not text:
        return ''

    # Remove special characters, keep only alphanumeric and spaces
    normalized = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)

    # Convert to lowercase
    normalized = normalized.lower()

    # Collapse multiple spaces to single space
    normalized = ' '.join(normalized.split())

    return normalized


def query_dicom_tag(tags_dict: dict, tag_keyword: str) -> Optional[any]:
    """
    Query specific DICOM tag from stored tags dictionary.

    Args:
        tags_dict: Dictionary of DICOM tags from extract_all_dicom_tags()
        tag_keyword: Tag keyword (e.g., "PatientID") or hex string (e.g., "00100020")

    Returns:
        Tag value or None if not found
    """
    from pydicom.datadict import keyword_dict

    # Try to convert keyword to tag number
    if tag_keyword in keyword_dict:
        tag_num = keyword_dict[tag_keyword]
        tag_key = f"{tag_num[0]:04X}{tag_num[1]:04X}"
    else:
        # Assume it's already a hex string
        tag_key = tag_keyword.upper()

    tag_data = tags_dict.get(tag_key, {})
    return tag_data.get('value')


# ============================================================================
# Thumbnail Generation Utilities
# ============================================================================

def generate_thumbnail(
    dcm: pydicom.Dataset,
    size: Tuple[int, int] = (150, 150),
    frame_number: int = 0,
    quality: int = 85
) -> BytesIO:
    """
    Generate thumbnail from DICOM file.

    Args:
        dcm: pydicom Dataset
        size: Thumbnail size as (width, height) tuple
        frame_number: Frame to use for multi-frame images
        quality: JPEG quality (1-100)

    Returns:
        BytesIO buffer containing JPEG thumbnail
    """
    # Extract frame
    pixel_array = extract_frame(dcm, frame_number)

    # Apply modality LUT
    pixel_array = apply_modality_lut(pixel_array, dcm)

    # Get default window/level
    center, width = get_default_window(dcm)

    # Apply windowing
    windowed = apply_windowing(pixel_array, center, width)

    # Handle photometric interpretation
    windowed = handle_photometric_interpretation(windowed, dcm)

    # Create PIL Image
    if len(windowed.shape) == 3:
        pil_image = Image.fromarray(windowed, mode='RGB')
    else:
        pil_image = Image.fromarray(windowed, mode='L')

    # Generate thumbnail (maintains aspect ratio)
    pil_image.thumbnail(size, Image.Resampling.LANCZOS)

    # Save to buffer
    output_buffer = BytesIO()
    pil_image.save(output_buffer, format='JPEG', quality=quality, optimize=True)
    output_buffer.seek(0)

    return output_buffer


def generate_series_thumbnails(series):
    """
    Generate thumbnails for a series (using middle image).

    Args:
        series: MedicalSeries instance

    Returns:
        Boolean indicating success
    """
    from django.core.files.base import ContentFile
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)

    try:
        images = series.images.order_by('instance_number')
        if images.count() == 0:
            logger.warning(f"No images found for series {series.id}")
            return False

        # Use middle image for thumbnail
        middle_image = images[images.count() // 2]
        dcm = pydicom.dcmread(middle_image.file.path, stop_before_pixels=False)

        # Update status
        series.thumbnail_generation_status = 'processing'
        series.save()

        # Generate thumbnails in three sizes
        sizes = {
            'small': (150, 150),
            'medium': (300, 300),
            'large': (512, 512)
        }

        for size_name, size_dims in sizes.items():
            thumbnail_buffer = generate_thumbnail(dcm, size=size_dims)
            filename = f"{series.series_instance_uid}_{size_name}.jpg"

            # Get the field (thumbnail_small, thumbnail_medium, thumbnail_large)
            field = getattr(series, f'thumbnail_{size_name}')

            # Save thumbnail
            field.save(filename, ContentFile(thumbnail_buffer.read()), save=False)

        # Update status
        series.thumbnail_generation_status = 'completed'
        series.thumbnail_generated_at = datetime.now()
        series.save()

        return True

    except Exception as e:
        logger.error(f"Failed to generate thumbnails for series {series.id}: {e}")
        series.thumbnail_generation_status = 'failed'
        series.save()
        return False


# ============================================================================
# Annotation Calculation Utilities
# ============================================================================

def calculate_distance_measurement(
    point1: dict,
    point2: dict,
    pixel_spacing: Optional[Tuple[float, float]] = None
) -> dict:
    """
    Calculate distance between two points.

    Args:
        point1: Dict with 'x' and 'y' keys (in pixels)
        point2: Dict with 'x' and 'y' keys (in pixels)
        pixel_spacing: Tuple of (row_spacing, column_spacing) in mm

    Returns:
        Dict with length_pixels, length_mm, and unit
    """
    import math

    # Calculate pixel distance
    dx = point2['x'] - point1['x']
    dy = point2['y'] - point1['y']
    pixel_distance = math.sqrt(dx**2 + dy**2)

    # Calculate physical distance if pixel spacing available
    if pixel_spacing and pixel_spacing[0] and pixel_spacing[1]:
        dx_mm = dx * pixel_spacing[1]  # column spacing
        dy_mm = dy * pixel_spacing[0]  # row spacing
        physical_distance = math.sqrt(dx_mm**2 + dy_mm**2)
    else:
        physical_distance = None

    return {
        'length_pixels': pixel_distance,
        'length_mm': physical_distance,
        'unit': 'mm' if physical_distance else 'pixels'
    }


def calculate_area_measurement(
    points: list,
    pixel_spacing: Optional[Tuple[float, float]] = None
) -> dict:
    """
    Calculate polygon area using Shoelace formula.

    Args:
        points: List of dicts with 'x' and 'y' keys
        pixel_spacing: Tuple of (row_spacing, column_spacing) in mm

    Returns:
        Dict with area_pixels, area_mm2, and unit
    """
    if len(points) < 3:
        return {
            'area_pixels': 0,
            'area_mm2': None,
            'unit': 'pixels²'
        }

    # Shoelace formula for polygon area
    area_pixels = 0
    n = len(points)

    for i in range(n):
        j = (i + 1) % n
        area_pixels += points[i]['x'] * points[j]['y']
        area_pixels -= points[j]['x'] * points[i]['y']

    area_pixels = abs(area_pixels) / 2

    # Calculate physical area if pixel spacing available
    if pixel_spacing and pixel_spacing[0] and pixel_spacing[1]:
        pixel_area_mm2 = pixel_spacing[0] * pixel_spacing[1]
        area_mm2 = area_pixels * pixel_area_mm2
    else:
        area_mm2 = None

    return {
        'area_pixels': area_pixels,
        'area_mm2': area_mm2,
        'unit': 'mm²' if area_mm2 else 'pixels²'
    }


def calculate_angle_measurement(points: list) -> dict:
    """
    Calculate angle between three points (vertex at point2).

    Args:
        points: List of exactly 3 dicts with 'x' and 'y' keys

    Returns:
        Dict with angle_degrees and angle_radians
    """
    import math

    if len(points) != 3:
        raise ValueError("Angle measurement requires exactly 3 points")

    p1, p2, p3 = points

    # Vectors from p2 to p1 and p2 to p3
    v1 = (p1['x'] - p2['x'], p1['y'] - p2['y'])
    v2 = (p3['x'] - p2['x'], p3['y'] - p2['y'])

    # Dot product and magnitudes
    dot_product = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2)

    if mag1 == 0 or mag2 == 0:
        return {
            'angle_degrees': 0,
            'angle_radians': 0
        }

    # Calculate angle
    cos_angle = max(-1, min(1, dot_product / (mag1 * mag2)))
    angle_rad = math.acos(cos_angle)
    angle_deg = math.degrees(angle_rad)

    return {
        'angle_degrees': angle_deg,
        'angle_radians': angle_rad
    }
