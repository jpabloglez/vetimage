"""
BIDS Packaging Utilities

Converts anonymized DICOM studies to NIfTI+BIDS or PNG+BIDS ZIP archives.
PHI is stripped from all JSON sidecars before packaging.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import pydicom
from django.conf import settings

logger = logging.getLogger(__name__)

# PHI keys to strip from dcm2niix-generated JSON sidecars
BIDS_JSON_PHI_KEYS = [
    'PatientName', 'PatientID', 'PatientBirthDate', 'PatientSex',
    'PatientAge', 'PatientWeight', 'PatientSize',
    'InstitutionName', 'InstitutionAddress', 'StationName',
    'ReferringPhysicianName', 'PerformingPhysicianName', 'OperatorsName',
    'AccessionNumber', 'StudyID',
]


def sanitize_bids_json(json_path: Path) -> dict:
    """Read dcm2niix-generated JSON, strip PHI keys, return cleaned dict."""
    with open(json_path) as f:
        data = json.load(f)
    for key in BIDS_JSON_PHI_KEYS:
        data.pop(key, None)
    return data


def infer_bids_datatype(modality: str) -> str:
    """Map DICOM modality → BIDS data type folder."""
    modality = (modality or '').upper()
    if modality in ('MR', 'CT', 'PT', 'MG', 'CR', 'DX', 'RF', 'US', 'XA'):
        return 'anat'
    if modality == 'NM':
        return 'pet'
    return 'anat'


def bids_filename_stem(anon_prefix: str, series_description: str,
                       modality: str, run_index: int) -> str:
    """Build a BIDS-compatible filename stem."""
    # Strip characters illegal in BIDS filenames (only alphanumeric and dash allowed)
    desc = re.sub(r'[^A-Za-z0-9]', '', series_description or '')[:20]
    suffix = desc if desc else modality.upper()
    run_str = str(run_index).zfill(2)
    return f"sub-{anon_prefix}_run-{run_str}_{suffix}"


def run_dcm2niix(dicom_dir: Path, output_dir: Path, stem: str) -> list:
    """
    Run dcm2niix on a directory of DICOM files.
    Returns list of .nii.gz paths produced.
    Raises RuntimeError if no output produced.
    """
    result = subprocess.run(
        ['dcm2niix', '-z', 'y', '-b', 'y', '-f', stem,
         '-o', str(output_dir), str(dicom_dir)],
        capture_output=True,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "dcm2niix exited %d for %s: %s",
            result.returncode, dicom_dir, result.stderr.decode(errors='replace')
        )

    nii_files = list(output_dir.glob(f"{stem}*.nii.gz"))
    if not nii_files:
        raise RuntimeError(
            f"dcm2niix produced no NIfTI output for {dicom_dir}. "
            f"stderr: {result.stderr.decode(errors='replace')[:500]}"
        )
    return nii_files


def _write_anonymized_dcm_dir(images, series, profile, anon_prefix, dest_dir):
    """Anonymize each image and write .dcm files to dest_dir."""
    from dicom_images.services.anonymization import AnonymizationService

    service = AnonymizationService()
    dest_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for img in images:
        if not img.file or not os.path.isfile(img.file.path):
            continue
        try:
            dcm = pydicom.dcmread(img.file.path)
        except Exception:
            logger.warning("Cannot read DICOM image %s", img.id)
            continue
        service.anonymize_dataset(dcm, profile=profile, prefix=anon_prefix)
        out_path = dest_dir / img.original_filename
        dcm.save_as(str(out_path))
        written += 1
    return written


def _dataset_description(anon_prefix: str) -> dict:
    return {
        "Name": f"Anonymized study {anon_prefix}",
        "BIDSVersion": "1.8.0",
        "GeneratedBy": [{"Name": "OpenMedLab", "Version": "1.0"}],
    }


def build_nifti_bids_zip(study, profile: str, anon_prefix: str) -> str:
    """
    Build a NIfTI+BIDS ZIP for the given study.
    Returns relative path under MEDIA_ROOT.
    """
    output_dir = Path(settings.MEDIA_ROOT) / 'anonymized'
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"bids_{uuid.uuid4().hex[:8]}.zip"
    zip_path = output_dir / zip_name

    work_dir = output_dir / f'tmp_{uuid.uuid4().hex[:12]}'
    work_dir.mkdir(parents=True)

    try:
        sub_dir = work_dir / f'sub-{anon_prefix}'
        series_qs = study.series.prefetch_related('images').all()

        modality_counter: dict[str, int] = {}
        any_success = False

        for series in series_qs:
            modality = series.modality or 'UNK'
            modality_counter[modality] = modality_counter.get(modality, 0) + 1
            run_idx = modality_counter[modality]

            stem = bids_filename_stem(anon_prefix, series.series_description, modality, run_idx)
            datatype = infer_bids_datatype(modality)

            dcm_dir = work_dir / f'dcm_{series.id}'
            nii_out = work_dir / f'nii_{series.id}'
            nii_out.mkdir(parents=True)

            images = series.images.order_by('instance_number')
            written = _write_anonymized_dcm_dir(images, series, profile, anon_prefix, dcm_dir)
            if not written:
                logger.warning("No images written for series %s — skipping", series.id)
                continue

            try:
                run_dcm2niix(dcm_dir, nii_out, stem)
            except RuntimeError as exc:
                logger.warning("dcm2niix failed for series %s: %s", series.id, exc)
                continue

            # Place output files under BIDS structure
            bids_series_dir = sub_dir / datatype
            bids_series_dir.mkdir(parents=True, exist_ok=True)

            for nii_file in nii_out.glob(f"{stem}*.nii.gz"):
                shutil.copy2(nii_file, bids_series_dir / nii_file.name)
                any_success = True

            for json_file in nii_out.glob(f"{stem}*.json"):
                clean = sanitize_bids_json(json_file)
                out_json = bids_series_dir / json_file.name
                with open(out_json, 'w') as f:
                    json.dump(clean, f, indent=2)

        if not any_success:
            raise RuntimeError("NIfTI conversion failed for all series in study.")

        # Write dataset_description.json
        with open(sub_dir / 'dataset_description.json', 'w') as f:
            json.dump(_dataset_description(anon_prefix), f, indent=2)

        # ZIP the sub-{prefix}/ tree
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fpath in sub_dir.rglob('*'):
                if fpath.is_file():
                    zf.write(fpath, fpath.relative_to(work_dir))

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return f"anonymized/{zip_name}"


def build_png_bids_zip(study, profile: str, anon_prefix: str) -> str:
    """
    Build a PNG+BIDS ZIP for the given study.
    Returns relative path under MEDIA_ROOT.
    """
    from dicom_images.services.anonymization import AnonymizationService
    from dicom_images.utils import dicom_to_image

    service = AnonymizationService()

    output_dir = Path(settings.MEDIA_ROOT) / 'anonymized'
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_name = f"bids_{uuid.uuid4().hex[:8]}.zip"
    zip_path = output_dir / zip_name

    work_dir = output_dir / f'tmp_{uuid.uuid4().hex[:12]}'
    work_dir.mkdir(parents=True)

    try:
        sub_dir = work_dir / f'sub-{anon_prefix}'
        series_qs = study.series.prefetch_related('images').all()

        modality_counter: dict[str, int] = {}
        any_success = False

        for series in series_qs:
            modality = series.modality or 'UNK'
            modality_counter[modality] = modality_counter.get(modality, 0) + 1
            run_idx = modality_counter[modality]

            stem = bids_filename_stem(anon_prefix, series.series_description, modality, run_idx)
            datatype = infer_bids_datatype(modality)

            bids_series_dir = sub_dir / datatype
            bids_series_dir.mkdir(parents=True, exist_ok=True)

            images = series.images.order_by('instance_number')
            for idx, img in enumerate(images, start=1):
                if not img.file or not os.path.isfile(img.file.path):
                    continue
                try:
                    dcm = pydicom.dcmread(img.file.path)
                except Exception:
                    logger.warning("Cannot read DICOM image %s", img.id)
                    continue

                service.anonymize_dataset(dcm, profile=profile, prefix=anon_prefix)

                instance_stem = f"{stem}_slice-{str(idx).zfill(4)}"

                # Convert to PNG
                try:
                    buf = dicom_to_image(dcm, output_format='PNG')
                    png_path = bids_series_dir / f"{instance_stem}.png"
                    with open(png_path, 'wb') as f:
                        f.write(buf.read())
                    any_success = True
                except Exception as exc:
                    logger.warning("PNG conversion failed for image %s: %s", img.id, exc)
                    continue

                # Build non-PHI sidecar from surviving tags
                sidecar = _extract_non_phi_metadata(dcm, modality)
                json_path = bids_series_dir / f"{instance_stem}.json"
                with open(json_path, 'w') as f:
                    json.dump(sidecar, f, indent=2)

        if not any_success:
            raise RuntimeError("PNG conversion failed for all images in study.")

        # Write dataset_description.json
        with open(sub_dir / 'dataset_description.json', 'w') as f:
            json.dump(_dataset_description(anon_prefix), f, indent=2)

        # ZIP the sub-{prefix}/ tree
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fpath in sub_dir.rglob('*'):
                if fpath.is_file():
                    zf.write(fpath, fpath.relative_to(work_dir))

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return f"anonymized/{zip_name}"


def _extract_non_phi_metadata(dcm, modality: str) -> dict:
    """Extract technical (non-PHI) DICOM tags for a BIDS JSON sidecar."""
    safe_tags = {
        'Modality': getattr(dcm, 'Modality', modality),
        'Rows': getattr(dcm, 'Rows', None),
        'Columns': getattr(dcm, 'Columns', None),
        'PixelSpacing': list(dcm.PixelSpacing) if hasattr(dcm, 'PixelSpacing') else None,
        'SliceThickness': getattr(dcm, 'SliceThickness', None),
        'SliceLocation': getattr(dcm, 'SliceLocation', None),
        'ImageOrientationPatient': (
            list(dcm.ImageOrientationPatient)
            if hasattr(dcm, 'ImageOrientationPatient') else None
        ),
        'ImagePositionPatient': (
            list(dcm.ImagePositionPatient)
            if hasattr(dcm, 'ImagePositionPatient') else None
        ),
        'WindowCenter': getattr(dcm, 'WindowCenter', None),
        'WindowWidth': getattr(dcm, 'WindowWidth', None),
        'RescaleIntercept': getattr(dcm, 'RescaleIntercept', None),
        'RescaleSlope': getattr(dcm, 'RescaleSlope', None),
        'PhotometricInterpretation': getattr(dcm, 'PhotometricInterpretation', None),
        'BitsAllocated': getattr(dcm, 'BitsAllocated', None),
        'BitsStored': getattr(dcm, 'BitsStored', None),
    }
    # Remove None values for cleanliness
    return {k: v for k, v in safe_tags.items() if v is not None}
