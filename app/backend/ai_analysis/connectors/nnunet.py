"""
nnU-Net Universal Connector

A single connector class that covers all nnU-Net-based segmentation models
(STU-Net, MIS-FM, A-Eval, and any future model using the nnU-Net framework).

Pipeline:
  1. prepare_input()   — DICOM series → NIfTI via dcm2niix, laid out as
                         nnU-Net expects: ``<case_id>_0000.nii.gz``
  2. dispatch_job()    — schedules ``run_nnunet_inference`` Celery task
                         (returns immediately, inference runs asynchronously)
  3. run_nnunet_inference() — nnUNetv2_predict subprocess → NIfTI mask,
                              task marked COMPLETED directly

Communication: local subprocess (no orchestrator, no gRPC).
Celery queue:  ``ai_jobs``

AIModel.metadata keys consumed by this connector:

    nnunet_dataset_id   (required) — nnU-Net dataset/task identifier,
                                     e.g. "Dataset010_Liver" or "10"
    nnunet_config       (optional) — trainer config, default "3d_fullres"
    nnunet_folds        (optional) — folds to use, default "all"
    nnunet_extra_args   (optional) — list of extra CLI flags

References:
  - nnU-Net v2: https://github.com/MIC-DKFZ/nnUNet
  - STU-Net:    https://github.com/vetimage/STU-Net
  - MIS-FM:     https://github.com/vetimage/MIS-FM
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from django.conf import settings

from .base import BaseAIConnector

logger = logging.getLogger(__name__)

# nnU-Net environment variable that controls where weights are stored
_NNUNET_RESULTS_ENV = "nnUNet_results"


class NNUNetConnector(BaseAIConnector):
    """
    Universal connector for nnU-Net-based segmentation models.

    Supports any model whose weights are installed in a directory accessible
    via the ``nnUNet_results`` environment variable.  Configure per-model
    behaviour through ``AIModel.metadata``:

    .. code-block:: python

        ai_model.metadata = {
            "nnunet_dataset_id": "Dataset010_Liver",
            "nnunet_config":     "3d_fullres",       # optional
            "nnunet_folds":      "all",               # optional
        }
    """

    # ------------------------------------------------------------------
    # Input preparation — DICOM → nnU-Net NIfTI layout
    # ------------------------------------------------------------------

    def prepare_input(self, task) -> Dict[str, Any]:
        """
        Convert the task's input DICOM image to a NIfTI file using dcm2niix,
        then rename it to follow nnU-Net's ``<case_id>_0000.nii.gz`` convention.

        The output is placed on the shared media volume so the celery worker
        can pass the path directly to ``nnUNetv2_predict``.

        Returns:
            dict with:
              - ``nnunet_input_dir``  (str): directory containing ``<case_id>_0000.nii.gz``
              - ``nnunet_case_id``    (str): 8-char case identifier (from task UUID)

        Raises:
            ValueError:   If the input image or DICOM file is missing.
            RuntimeError: If dcm2niix fails or produces no output.
        """
        if not task.input_image or not task.input_image.file:
            raise ValueError(f"Task {task.id}: no input image file attached")

        dicom_path = os.path.join(settings.MEDIA_ROOT, task.input_image.file.name)
        if not Path(dicom_path).exists():
            raise ValueError(f"Task {task.id}: DICOM file not found: {dicom_path}")

        case_id = str(task.id)[:8]
        work_dir = Path(settings.MEDIA_ROOT) / "nnunet_inputs" / f"task_{task.id}"
        work_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Task %s: converting DICOM → NIfTI (dcm2niix) in %s", task.id, work_dir)

        result = subprocess.run(
            ["dcm2niix", "-z", "y", "-f", "converted", "-o", str(work_dir), dicom_path],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Task {task.id}: dcm2niix failed (rc={result.returncode}). "
                f"stderr: {result.stderr[-1000:]}"
            )

        # Find the primary NIfTI output (no alphabetical suffix = primary volume)
        primary = work_dir / "converted.nii.gz"
        if not primary.exists():
            candidates = sorted(work_dir.glob("*.nii.gz")) or sorted(work_dir.glob("*.nii"))
            if not candidates:
                raise RuntimeError(
                    f"Task {task.id}: dcm2niix completed but no NIfTI file found in {work_dir}"
                )
            primary = candidates[0]

        # Rename to nnU-Net convention: <case_id>_0000.nii.gz
        nnunet_file = work_dir / f"{case_id}_0000.nii.gz"
        shutil.move(str(primary), str(nnunet_file))

        logger.info("Task %s: nnU-Net input prepared: %s", task.id, nnunet_file)

        return {
            "nnunet_input_dir": str(work_dir),
            "nnunet_case_id":   case_id,
        }

    # ------------------------------------------------------------------
    # Dispatch — schedule the inference Celery task
    # ------------------------------------------------------------------

    def dispatch_job(self, task) -> Dict[str, Any]:
        """
        Schedule ``run_nnunet_inference`` as a Celery task and return immediately.

        The inference task runs ``nnUNetv2_predict`` asynchronously and marks
        the AnalysisTask as COMPLETED (or FAILED) when done.

        Returns:
            dict with ``service_job_id`` and ``status='queued'``.

        Raises:
            ValueError: If required metadata keys are missing.
        """
        dataset_id = (task.model.metadata or {}).get("nnunet_dataset_id")
        if not dataset_id:
            raise ValueError(
                f"AIModel '{task.model.key}' is missing required metadata key "
                "'nnunet_dataset_id'. Add it via the admin or seed command."
            )

        from ..tasks import run_nnunet_inference
        run_nnunet_inference.apply_async(
            args=[str(task.id)],
            queue="ai_jobs",
        )

        return {
            "service_job_id": f"nnunet-{task.id}",
            "status": "queued",
        }

    # ------------------------------------------------------------------
    # Parameter validation
    # ------------------------------------------------------------------

    def validate_parameters(self, parameters: Dict) -> bool:
        """
        Validate that the model metadata contains the required nnU-Net keys.
        User-supplied parameters are optional for nnU-Net (no required runtime params).
        """
        dataset_id = (self.ai_model.metadata or {}).get("nnunet_dataset_id")
        if not dataset_id:
            raise ValueError(
                f"AIModel '{self.ai_model.key}' is missing 'nnunet_dataset_id' "
                "in metadata. Cannot run nnU-Net inference."
            )
        return True

    # ------------------------------------------------------------------
    # CLI command builder (used by run_nnunet_inference)
    # ------------------------------------------------------------------

    @staticmethod
    def build_predict_command(
        input_dir: Path,
        output_dir: Path,
        dataset_id: str,
        config: str = "3d_fullres",
        folds: str = "all",
        extra_args: list | None = None,
    ) -> list[str]:
        """
        Build the ``nnUNetv2_predict`` command.

        Args:
            input_dir:   Directory containing ``<case_id>_0000.nii.gz``.
            output_dir:  Directory where prediction NIfTI will be written.
            dataset_id:  nnU-Net dataset identifier (e.g. ``"Dataset010_Liver"``).
            config:      Trainer configuration (default ``"3d_fullres"``).
            folds:       Folds to use, ``"all"`` or e.g. ``"0 1 2"`` (default ``"all"``).
            extra_args:  Additional CLI flags appended verbatim.

        Returns:
            List of strings ready for :func:`subprocess.run`.
        """
        cmd = [
            "nnUNetv2_predict",
            "-i", str(input_dir),
            "-o", str(output_dir),
            "-d", str(dataset_id),
            "-c", config,
            "-f", *folds.split(),
        ]
        if extra_args:
            cmd.extend(extra_args)
        return cmd
