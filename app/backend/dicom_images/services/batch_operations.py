"""
Batch Operations Service

Handles bulk delete, export, and analyze operations on studies.
"""

import logging
import os
import uuid
import zipfile
from pathlib import Path

from django.conf import settings

from dicom_images.models import MedicalStudy, MedicalImage

logger = logging.getLogger(__name__)


class BatchOperationService:
    """Perform batch operations on multiple studies."""

    def batch_delete(self, study_ids, user):
        """
        Delete multiple studies and all related data.

        Returns the count of deleted studies.
        """
        studies = MedicalStudy.objects.filter(
            id__in=study_ids, uploaded_by=user,
        )
        count = studies.count()
        studies.delete()
        return count

    def batch_export(self, study_ids, user):
        """
        Export all DICOM files from the given studies into a ZIP.

        Returns the path to the output ZIP relative to MEDIA_ROOT.
        """
        studies = MedicalStudy.objects.filter(
            id__in=study_ids, uploaded_by=user,
        )
        images = MedicalImage.objects.filter(
            series__study__in=studies,
        ).select_related('series__study')

        output_dir = Path(settings.MEDIA_ROOT) / 'exports'
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_name = f"export_{uuid.uuid4().hex[:12]}.zip"
        zip_path = output_dir / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for img in images:
                if not img.file or not os.path.isfile(img.file.path):
                    continue
                arcname = (
                    f"{img.series.study.study_instance_uid}/"
                    f"{img.series.series_instance_uid}/"
                    f"{img.original_filename}"
                )
                zf.write(img.file.path, arcname)

        return f"exports/{zip_name}"

    def batch_analyze(self, study_ids, model_key, parameters, user):
        """
        Create an AnalysisTask per image in the given studies.

        Returns a list of created task IDs.
        """
        from ai_analysis.models import AIModel, AnalysisTask

        model = AIModel.objects.get(key=model_key, is_active=True)
        images = MedicalImage.objects.filter(
            series__study__id__in=study_ids,
            series__study__uploaded_by=user,
        )

        task_ids = []
        for img in images:
            task = AnalysisTask.objects.create(
                input_image=img,
                model=model,
                created_by=user,
                status='PENDING',
                parameters=parameters or {},
            )
            task_ids.append(str(task.id))

        return task_ids
