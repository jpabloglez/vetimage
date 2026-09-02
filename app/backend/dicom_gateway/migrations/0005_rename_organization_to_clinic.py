"""Rename PACSConfiguration.receiving_organization -> receiving_clinic."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dicom_gateway', '0004_enhance_pacs_config_with_api_keys'),
        ('users', '0014_rename_organization_to_clinic'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pacsconfiguration',
            old_name='receiving_organization',
            new_name='receiving_clinic',
        ),
    ]
