from django.db import migrations

from dicom_images.utils import normalize_text_for_search


def backfill_patient_display_fields(apps, schema_editor):
    """
    Studies linked to an AnimalPatient before this fix never had their
    patient_name/patient_id synced from the link — they were frozen at
    whatever the source DICOM file's tags were (often blank/generic),
    showing "Unknown Patient" in the viewer despite a real patient being
    linked. Backfill display fields for every already-linked study.
    """
    MedicalStudy = apps.get_model('dicom_images', 'MedicalStudy')

    for study in MedicalStudy.objects.filter(animal_patient__isnull=False).select_related('animal_patient'):
        study.patient_name = study.animal_patient.name
        study.patient_id = str(study.animal_patient_id)
        study.patient_name_normalized = normalize_text_for_search(study.animal_patient.name)
        study.save(update_fields=['patient_name', 'patient_id', 'patient_name_normalized'])


def noop_reverse(apps, schema_editor):
    """Not reversible — the original (pre-link) patient_name/patient_id values aren't recoverable."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('dicom_images', '0009_studysharelink'),
    ]

    operations = [
        migrations.RunPython(backfill_patient_display_fields, noop_reverse),
    ]
