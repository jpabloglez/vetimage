"""
DICOM SEG Conversion Services

Two-direction pipeline using the dcmqi command-line tools:

  NIfTI → DICOM SEG  (itkimage2segimage)
    NIfTI mask + source DICOM series + JSON metadata → DICOM SEG (.dcm)

  DICOM SEG → NIfTI  (segimage2itkimage)
    DICOM SEG (.dcm) → NIfTI files + JSON metadata per segment

References:
  - dcmqi docs (NIfTI→SEG):  https://qiicr.gitbook.io/dcmqi-guide/opening/cmd_tools/seg/itkimage2segimage
  - dcmqi docs (SEG→NIfTI):  https://qiicr.gitbook.io/dcmqi-guide/opening/cmd_tools/seg/segimage2itkimage
  - SNOMED codes:             https://browser.ihtsdotools.org/
"""

import json
import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SNOMED CT anatomy codes — (CodeValue, CodingSchemeDesignator, CodeMeaning)
# Keys are lowercase with underscores (also matched with spaces and hyphens).
# ---------------------------------------------------------------------------

_ANATOMY_CODES: dict[str, tuple[str, str, str]] = {
    # Abdominal organs (A-Eval 8-organ set)
    "liver":             ("10200004", "SCT", "Liver"),
    "right_kidney":      ("9846003",  "SCT", "Right Kidney"),
    "left_kidney":       ("18639004", "SCT", "Left Kidney"),
    "kidney":            ("64033007", "SCT", "Kidney"),
    "spleen":            ("78961009", "SCT", "Spleen"),
    "pancreas":          ("15776009", "SCT", "Pancreas"),
    "gallbladder":       ("28231008", "SCT", "Gallbladder"),
    "esophagus":         ("32849002", "SCT", "Esophagus"),
    "stomach":           ("69695003", "SCT", "Stomach"),
    # Thoracic
    "lung":              ("39607008", "SCT", "Lung"),
    "right_lung":        ("3341006",  "SCT", "Right Lung"),
    "left_lung":         ("41224006", "SCT", "Left Lung"),
    "heart":             ("80891009", "SCT", "Heart"),
    "aorta":             ("15825003", "SCT", "Aorta"),
    "trachea":           ("44567001", "SCT", "Trachea"),
    # Abdomen / retroperitoneum
    "colon":             ("71854001", "SCT", "Colon"),
    "rectum":            ("34402009", "SCT", "Rectum"),
    "duodenum":          ("38848004", "SCT", "Duodenum"),
    "small_intestine":   ("30315005", "SCT", "Small Intestine"),
    "adrenal_gland":     ("23451007", "SCT", "Adrenal Gland"),
    "right_adrenal":     ("30024000", "SCT", "Right Adrenal Gland"),
    "left_adrenal":      ("67169003", "SCT", "Left Adrenal Gland"),
    "inferior_vena_cava": ("64131007", "SCT", "Inferior Vena Cava"),
    "portal_vein":       ("32764006", "SCT", "Portal Vein"),
    "bladder":           ("89837001", "SCT", "Urinary Bladder"),
    "prostate":          ("41216001", "SCT", "Prostate"),
    "uterus":            ("35039007", "SCT", "Uterus"),
    # Head / neuro
    "brain":             ("12738006", "SCT", "Brain"),
    "spinal_cord":       ("2748008",  "SCT", "Spinal Cord"),
    # Musculoskeletal
    "femur":             ("71341001", "SCT", "Femur"),
    # Lesion / tumour (non-anatomical)
    "tumor":             ("108369006", "SCT", "Tumor"),
    "lesion":            ("52988006",  "SCT", "Lesion"),
    "nodule":            ("27925004",  "SCT", "Nodule"),
    # Generic fallback
    "tissue":            ("85756007", "SCT", "Tissue"),
}

# Category codes
_CAT_ANATOMICAL = {
    "CodeValue": "91723000",
    "CodingSchemeDesignator": "SCT",
    "CodeMeaning": "Anatomical Structure",
}
_CAT_MORPHOLOGICAL = {
    "CodeValue": "49755003",
    "CodingSchemeDesignator": "SCT",
    "CodeMeaning": "Morphologically Abnormal Structure",
}
_LESION_KEYS = {"tumor", "lesion", "nodule"}

# Colour palette — one colour per segment (cycles if more than 16 labels)
_COLOURS = [
    [255, 0,   0  ],  # red
    [0,   255, 0  ],  # green
    [0,   0,   255],  # blue
    [255, 255, 0  ],  # yellow
    [0,   255, 255],  # cyan
    [255, 0,   255],  # magenta
    [255, 128, 0  ],  # orange
    [128, 0,   255],  # purple
    [0,   128, 255],  # sky blue
    [255, 0,   128],  # rose
    [0,   255, 128],  # spring green
    [128, 255, 0  ],  # chartreuse
    [64,  0,   128],  # dark purple
    [0,   64,  128],  # dark blue
    [128, 64,  0  ],  # brown
    [64,  128, 0  ],  # olive
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise_label(name: str) -> str:
    """Lowercase, replace spaces/hyphens with underscores for dict lookup."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _lookup_anatomy(name: str) -> tuple[tuple[str, str, str], dict]:
    """
    Return (type_code_tuple, category_code_dict) for a label name.
    Falls back to generic 'Tissue' / Anatomical Structure if unknown.
    """
    key = _normalise_label(name)
    type_code = _ANATOMY_CODES.get(key, _ANATOMY_CODES["tissue"])
    category = _CAT_MORPHOLOGICAL if key in _LESION_KEYS else _CAT_ANATOMICAL
    return type_code, category


def _make_segment_attribute(label_id: int, label_name: str, colour: list) -> dict:
    """Build a single dcmqi segment attribute dict."""
    type_code, category = _lookup_anatomy(label_name)
    return {
        "labelID": label_id,
        "SegmentDescription": label_name,
        "SegmentAlgorithmType": "AUTOMATIC",
        "SegmentAlgorithmName": "OpenMedLab",
        "recommendedDisplayRGBValue": colour,
        "SegmentedPropertyCategoryCodeSequence": category,
        "SegmentedPropertyTypeCodeSequence": {
            "CodeValue":               type_code[0],
            "CodingSchemeDesignator":  type_code[1],
            "CodeMeaning":             type_code[2],
        },
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_dcmqi_metadata(
    label_map: dict,
    series_description: str = "AI Segmentation",
    algorithm_name: str = "OpenMedLab",
    series_number: int = 300,
) -> dict:
    """
    Build the dcmqi JSON metadata structure from a label_map.

    Args:
        label_map:          {str(label_id): label_name} e.g. {'1': 'liver', '2': 'spleen'}
        series_description: DICOM SeriesDescription tag for the SEG object
        algorithm_name:     Algorithm name stored per-segment
        series_number:      DICOM SeriesNumber (choose one unlikely to collide)

    Returns:
        dict ready for json.dumps() — pass as --inputMetadata to itkimage2segimage.
    """
    if not label_map:
        raise ValueError("label_map must not be empty")

    segment_attrs = []
    for idx, (label_id_str, label_name) in enumerate(
        sorted(label_map.items(), key=lambda x: int(x[0]))
    ):
        colour = _COLOURS[idx % len(_COLOURS)]
        attr = _make_segment_attribute(int(label_id_str), label_name, colour)
        attr["SegmentAlgorithmName"] = algorithm_name
        # dcmqi expects segmentAttributes as list-of-lists:
        # outer index = input NIfTI file index, inner list = segments in that file
        segment_attrs.append([attr])

    return {
        "$schema": (
            "https://raw.githubusercontent.com/qiicr/dcmqi/master"
            "/doc/schemas/seg-schema.json#"
        ),
        "ContentCreatorName": "OpenMedLab",
        "SeriesDescription": series_description,
        "SeriesNumber": str(series_number),
        "InstanceNumber": "1",
        "segmentAttributes": segment_attrs,
        "BodyPartExamined": "",
    }


def write_source_dicoms(series, dest_dir: Path) -> int:
    """
    Copy all DICOM files of *series* into *dest_dir*.

    Returns the number of files written.
    Raises RuntimeError if no files could be written.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for image in series.images.order_by("instance_number"):
        if not image.file:
            continue
        src = Path(image.file.path)
        if not src.is_file():
            logger.warning("DICOM file missing on disk: %s", src)
            continue
        shutil.copy2(src, dest_dir / (image.original_filename or src.name))
        written += 1

    if written == 0:
        raise RuntimeError(
            f"No DICOM files found for series {series.series_instance_uid}"
        )
    return written


def run_itkimage2segimage(
    nifti_path: Path,
    dicom_dir: Path,
    metadata_json_path: Path,
    output_path: Path,
    timeout: int = 300,
) -> Path:
    """
    Run dcmqi ``itkimage2segimage`` to convert a NIfTI segmentation mask to a
    DICOM SEG object.

    Args:
        nifti_path:         Absolute path to the NIfTI mask (.nii or .nii.gz)
        dicom_dir:          Directory containing the source DICOM series
        metadata_json_path: Path to the dcmqi metadata JSON file
        output_path:        Desired output path for the generated .dcm file
        timeout:            Subprocess timeout in seconds (default 300)

    Returns:
        *output_path* on success.

    Raises:
        FileNotFoundError:  If the NIfTI or metadata file does not exist.
        RuntimeError:       If itkimage2segimage fails or produces no output.
    """
    if not nifti_path.is_file():
        raise FileNotFoundError(f"NIfTI mask not found: {nifti_path}")
    if not metadata_json_path.is_file():
        raise FileNotFoundError(f"Metadata JSON not found: {metadata_json_path}")

    cmd = [
        "itkimage2segimage",
        "--inputImageList",    str(nifti_path),
        "--inputDICOMDirectory", str(dicom_dir),
        "--outputDICOM",       str(output_path),
        "--inputMetadata",     str(metadata_json_path),
        "--useLabelIDAsSegmentNumber",
    ]
    logger.info("itkimage2segimage cmd: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.stdout:
        logger.debug("itkimage2segimage stdout: %s", result.stdout)
    if result.stderr:
        logger.debug("itkimage2segimage stderr: %s", result.stderr)

    if result.returncode != 0 or not output_path.is_file():
        raise RuntimeError(
            f"itkimage2segimage failed (rc={result.returncode}). "
            f"stderr: {result.stderr[:1000]}"
        )

    logger.info("DICOM SEG written to %s (%d bytes)", output_path, output_path.stat().st_size)
    return output_path


# ---------------------------------------------------------------------------
# DICOM SEG → NIfTI (segimage2itkimage)
# ---------------------------------------------------------------------------

def run_segimage2itkimage(
    dicom_seg_path: Path,
    output_dir: Path,
    prefix: str = "seg",
    merge_segments: bool = True,
    timeout: int = 300,
) -> list[dict]:
    """
    Run dcmqi ``segimage2itkimage`` to convert a DICOM SEG object to NIfTI files.

    Each segment is written as a separate ``<prefix>_<N>.nii`` file accompanied
    by a ``<prefix>_<N>.json`` metadata file.  With ``--mergeSegments`` all
    non-overlapping segments are merged into a single ``<prefix>.nii`` /
    ``<prefix>.json`` pair.

    Args:
        dicom_seg_path: Absolute path to the DICOM SEG file (.dcm).
        output_dir:     Directory where output files will be written (created if absent).
        prefix:         Filename prefix for output files (default ``"seg"``).
        merge_segments: Pass ``--mergeSegments`` flag (default True).
        timeout:        Subprocess timeout in seconds (default 300).

    Returns:
        List of dicts, one per NIfTI output file::

            [
                {
                    "nifti_path":     Path,        # absolute path to .nii file
                    "metadata_path":  Path | None, # absolute path to companion .json
                    "metadata":       dict,        # parsed JSON metadata (or {})
                    "segment_number": int | None,  # extracted from filename
                }
            ]

    Raises:
        FileNotFoundError: If ``dicom_seg_path`` does not exist.
        RuntimeError:      If ``segimage2itkimage`` fails or produces no output.
    """
    if not dicom_seg_path.is_file():
        raise FileNotFoundError(f"DICOM SEG file not found: {dicom_seg_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "segimage2itkimage",
        "--inputDICOM",      str(dicom_seg_path),
        "--outputDirectory", str(output_dir),
        "--prefix",          prefix,
        "--outputType",      "nii",
    ]
    if merge_segments:
        cmd.append("--mergeSegments")

    logger.info("segimage2itkimage cmd: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.stdout:
        logger.debug("segimage2itkimage stdout: %s", result.stdout)
    if result.stderr:
        logger.debug("segimage2itkimage stderr: %s", result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"segimage2itkimage failed (rc={result.returncode}). "
            f"stderr: {result.stderr[:1000]}"
        )

    # Collect produced NIfTI files (.nii.gz checked before .nii to avoid double-match)
    nifti_files = sorted(
        {p for p in output_dir.glob(f"{prefix}*.nii*") if p.suffix in (".nii", ".gz")},
        key=lambda p: p.name,
    )

    if not nifti_files:
        raise RuntimeError(
            f"segimage2itkimage produced no NIfTI output in {output_dir} "
            f"(prefix={prefix!r})"
        )

    segments = []
    for nifti_path in nifti_files:
        stem = nifti_path.name.replace(".nii.gz", "").replace(".nii", "")
        meta_path = output_dir / f"{stem}.json"

        metadata: dict = {}
        if meta_path.is_file():
            try:
                metadata = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                logger.warning("Could not parse metadata JSON: %s", meta_path)

        # Extract segment number from trailing "_<N>" suffix
        seg_number: int | None = None
        parts = stem.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            seg_number = int(parts[1])

        segments.append({
            "nifti_path":     nifti_path,
            "metadata_path":  meta_path if meta_path.is_file() else None,
            "metadata":       metadata,
            "segment_number": seg_number,
        })

    logger.info(
        "segimage2itkimage produced %d NIfTI file(s) in %s",
        len(segments), output_dir,
    )
    return segments


def convert_dicom_seg_to_nifti(
    dicom_seg_path: Path,
    prefix: str = "seg",
    merge_segments: bool = True,
) -> tuple[list[dict], Path]:
    """
    Full pipeline: DICOM SEG file → NIfTI files stored under MEDIA_ROOT.

    Steps:
      1. Run ``segimage2itkimage`` in a unique subdirectory of
         ``MEDIA_ROOT/nifti_from_seg/``.
      2. Return the segment list and the output directory (caller is responsible
         for cleanup or serving the files).

    Args:
        dicom_seg_path: Absolute path to the input DICOM SEG file.
        prefix:         Filename prefix for output files.
        merge_segments: Whether to merge non-overlapping segments into one file.

    Returns:
        Tuple of ``(segment_list, output_dir)`` where ``segment_list`` is the
        list returned by :func:`run_segimage2itkimage` and ``output_dir`` is the
        directory containing all generated files.

    Raises:
        FileNotFoundError: If ``dicom_seg_path`` does not exist.
        RuntimeError:      If conversion fails.
    """
    base_out = Path(settings.MEDIA_ROOT) / "nifti_from_seg"
    output_dir = base_out / uuid.uuid4().hex[:16]
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        segments = run_segimage2itkimage(
            dicom_seg_path=dicom_seg_path,
            output_dir=output_dir,
            prefix=prefix,
            merge_segments=merge_segments,
        )
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise

    return segments, output_dir


def create_dicom_seg(
    nifti_path: Path,
    series,
    label_map: dict,
    series_description: str = "AI Segmentation",
    algorithm_name: str = "OpenMedLab",
) -> Path:
    """
    Full pipeline: NIfTI mask + DICOM series + label map → DICOM SEG file.

    Steps:
      1. Copy source DICOM files to a temp directory.
      2. Build the dcmqi metadata JSON from *label_map*.
      3. Run ``itkimage2segimage``.
      4. Move the output to a permanent location under ``MEDIA_ROOT/dicom_seg/``.
      5. Clean up the temp directory.

    Args:
        nifti_path:         Absolute path to the NIfTI segmentation mask.
        series:             ``MedicalSeries`` ORM instance (must have .images prefetched
                            or queryable).
        label_map:          {str(label_id): label_name} — must not be empty.
        series_description: DICOM SeriesDescription for the SEG object.
        algorithm_name:     Algorithm name stored in each segment attribute.

    Returns:
        Absolute path to the generated DICOM SEG file.

    Raises:
        ValueError:    If *label_map* is empty.
        RuntimeError:  If the conversion fails.
    """
    output_dir = Path(settings.MEDIA_ROOT) / "dicom_seg"
    output_dir.mkdir(parents=True, exist_ok=True)

    work_dir = output_dir / f"tmp_{uuid.uuid4().hex[:12]}"
    work_dir.mkdir(parents=True)

    try:
        # 1. Copy source DICOMs
        dicom_dir = work_dir / "source"
        write_source_dicoms(series, dicom_dir)

        # 2. Write dcmqi metadata JSON
        metadata = build_dcmqi_metadata(
            label_map=label_map,
            series_description=series_description,
            algorithm_name=algorithm_name,
        )
        metadata_path = work_dir / "seg_metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        # 3. Run conversion (output goes into output_dir, not work_dir)
        output_path = output_dir / f"seg_{uuid.uuid4().hex[:16]}.dcm"
        run_itkimage2segimage(nifti_path, dicom_dir, metadata_path, output_path)

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return output_path
