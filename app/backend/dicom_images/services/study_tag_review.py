"""
Study Tag Review Service

Lets a user confirm/correct key DICOM identity tags (PatientName, PatientID,
AccessionNumber) for a whole study right after upload — writing the values
both to the MedicalStudy DB row and to every on-disk instance file, so
DICOMweb WADO-RS metadata (read live from the files) and the app's own
display fields stay consistent instead of diverging like they did before.
"""

import logging

import pydicom

from dicom_images.models import MedicalImage
from dicom_images.utils import extract_all_dicom_tags, normalize_text_for_search

logger = logging.getLogger(__name__)

# field name -> (DICOM tag as (group, element), VR) used when the tag is
# missing from a file and needs to be added rather than overwritten.
FIELD_TAG_MAP = {
    'patient_name': ((0x0010, 0x0010), 'PN'),
    'patient_id': ((0x0010, 0x0020), 'LO'),
    'accession_number': ((0x0008, 0x0050), 'SH'),
}


class StudyTagReviewService:
    """Read and update the reviewable identity tags for a study."""

    def get_review_fields(self, study):
        return {
            'patient_name': study.patient_name,
            'patient_id': study.patient_id,
            'accession_number': study.accession_number,
        }

    def update_review_fields(self, study, field_values):
        """
        Apply *field_values* (a subset of FIELD_TAG_MAP's keys) to *study*
        and to every instance file under it.

        Returns (files_updated, files_total) — on-disk writes are best
        effort per file so one unreadable/missing file doesn't block the
        rest of the study.
        """
        update_fields = ['updated_at']
        for field, value in field_values.items():
            setattr(study, field, value)
            update_fields.append(field)
        if 'patient_name' in field_values:
            study.patient_name_normalized = normalize_text_for_search(study.patient_name)
            update_fields.append('patient_name_normalized')
        study.save(update_fields=update_fields)

        images = MedicalImage.objects.filter(series__study=study)
        files_total = images.count()
        files_updated = 0
        for image in images:
            try:
                self._write_tags_to_file(image, field_values)
                files_updated += 1
            except Exception:
                logger.warning(
                    "Failed to write reviewed DICOM tags to disk for image %s (study %s)",
                    image.id, study.id, exc_info=True,
                )

        return files_updated, files_total

    def _write_tags_to_file(self, image, field_values):
        dcm = pydicom.dcmread(image.file.path)

        for field, value in field_values.items():
            (group, element), vr = FIELD_TAG_MAP[field]
            tag = pydicom.tag.Tag(group, element)
            if tag in dcm:
                dcm[tag].value = value
            else:
                dcm.add_new(tag, vr, value)

        dcm.save_as(image.file.path)

        image.dicom_tags = extract_all_dicom_tags(dcm)
        image.save(update_fields=['dicom_tags'])
