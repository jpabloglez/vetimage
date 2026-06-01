"""
FastSurfer AI Connector

Handles DICOM→NIfTI conversion and orchestrator dispatch for the FastSurfer
whole-brain MRI segmentation model.

Pipeline:
  1. prepare_input()  — converts the T1w DICOM file to NIfTI via dcm2niix
  2. dispatch_job()   — fallback for Celery (USE_ORCHESTRATOR=False) mode
  3. Orchestrator dispatches gRPC call to fastsurfer-service:50051

Requires dcm2niix on PATH (pre-installed in the backend Docker image).
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from django.conf import settings

from .base import BaseAIConnector

logger = logging.getLogger(__name__)


class FastSurferConnector(BaseAIConnector):
    """
    Connector for the FastSurfer whole-brain segmentation model.

    Supported modality: T1-weighted MRI (DICOM → NIfTI conversion happens here).
    Communication path: gRPC via Orchestrator (USE_ORCHESTRATOR=True).
    """

    required_parameters = []
    default_parameters = {
        "device": "cuda",
        "threads": 4,
        "use_3T": True,
    }

    # ------------------------------------------------------------------
    # Input preparation
    # ------------------------------------------------------------------

    def prepare_input(self, task) -> Dict[str, Any]:
        """
        Convert the task's T1w DICOM file to NIfTI format before dispatch.

        Uses dcm2niix to perform the conversion.  The generated .nii.gz file
        path and a short subject ID are returned as extra parameters that get
        merged into task.parameters before the orchestrator call.

        Args:
            task: AnalysisTask instance with task.input_image pointing to a
                  T1-weighted MRI DICOM file.

        Returns:
            dict with:
                - nifti_path  (str): Absolute path to the converted .nii.gz file
                - subject_id  (str): 8-character subject identifier

        Raises:
            ValueError: If the input image or DICOM file is missing.
            RuntimeError: If dcm2niix conversion fails.
        """
        if not task.input_image:
            raise ValueError(f"Task {task.id} has no input image attached")

        file_name = task.input_image.file.name if task.input_image.file else None
        if not file_name:
            raise ValueError(
                f"Task {task.id}: input image has no file attached "
                "(file field is empty)"
            )

        dicom_path = os.path.join(settings.MEDIA_ROOT, file_name)

        if not Path(dicom_path).exists():
            raise ValueError(
                f"Task {task.id}: DICOM file not found at path: {dicom_path}"
            )

        subject_id = str(task.id)[:8]

        # Output must be on the shared media volume so the fastsurfer-service
        # container can read the file at the same path.
        # /tmp/ is local to the backend container — the fastsurfer container
        # cannot see files placed there.
        nifti_dir = Path(settings.MEDIA_ROOT) / "nifti" / f"fastsurfer_{task.id}"
        nifti_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Task %s: converting DICOM → NIfTI (dcm2niix) in %s",
            task.id,
            nifti_dir,
        )

        result = subprocess.run(
            [
                "dcm2niix",
                "-z", "y",       # gzip output
                "-f", "input",   # fixed output filename prefix
                "-o", str(nifti_dir),
                dicom_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error("dcm2niix stderr: %s", result.stderr)
            raise RuntimeError(
                f"Task {task.id}: dcm2niix conversion failed "
                f"(exit {result.returncode}).\nstderr: {result.stderr[-1000:]}"
            )

        # Find the generated NIfTI file.
        # dcm2niix may create multiple files when the DICOM has several volumes
        # (e.g. input.nii.gz + inputb.nii.gz).  Always prefer the exact prefix
        # match (no alphabetical suffix = primary volume); fall back to the
        # lexicographically first file so selection is deterministic.
        primary = nifti_dir / "input.nii.gz"
        if primary.exists():
            nifti_path = str(primary)
        else:
            nifti_files = sorted(nifti_dir.glob("*.nii.gz"))
            if not nifti_files:
                nifti_files = sorted(nifti_dir.glob("*.nii"))
            if not nifti_files:
                raise RuntimeError(
                    f"Task {task.id}: dcm2niix completed but no NIfTI file found in {nifti_dir}"
                )
            nifti_path = str(nifti_files[0])

        logger.info("Task %s: NIfTI file created at %s", task.id, nifti_path)

        return {
            "nifti_path": nifti_path,
            "subject_id": subject_id,
        }

    # ------------------------------------------------------------------
    # Celery dispatch (fallback when USE_ORCHESTRATOR=False)
    # ------------------------------------------------------------------

    def dispatch_job(self, task) -> Dict[str, Any]:
        """
        Celery/REST fallback — not the primary execution path for FastSurfer.

        FastSurfer uses the gRPC orchestrator path (USE_ORCHESTRATOR=True).
        This placeholder allows the connector to satisfy the abstract contract
        and provides a meaningful status for Celery-mode deployments.
        """
        logger.warning(
            "Task %s: FastSurfer connector dispatch_job called via Celery mode. "
            "FastSurfer is designed to run via the gRPC orchestrator. "
            "Set USE_ORCHESTRATOR=True for production use.",
            task.id,
        )
        return {
            "service_job_id": f"fastsurfer-placeholder-{task.id}",
            "status": "queued",
        }

    # ------------------------------------------------------------------
    # Parameter validation
    # ------------------------------------------------------------------

    def validate_parameters(self, parameters: Dict) -> bool:
        """
        Validate FastSurfer-specific parameters.

        Checks:
          - device ∈ {'cuda', 'cpu'}
          - threads is an integer in [1, 16]

        Args:
            parameters: User-supplied parameters dict.

        Returns:
            True if valid.

        Raises:
            ValueError: If any parameter is outside the allowed range.
        """
        device = parameters.get("device", "cuda")
        if device not in ("cuda", "cpu"):
            raise ValueError(
                f"Invalid device '{device}'. Must be 'cuda' or 'cpu'."
            )

        threads = parameters.get("threads", 4)
        try:
            threads = int(threads)
        except (TypeError, ValueError):
            raise ValueError(f"threads must be an integer, got: {threads!r}")
        if not (1 <= threads <= 16):
            raise ValueError(
                f"threads must be between 1 and 16, got: {threads}"
            )

        return True
