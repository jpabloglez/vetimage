"""Rename Owner.organization and ReferringClinic.organization -> clinic.

Hand-written: autodetection reads these as remove+add, which would drop the
FK column and orphan every owner and partner clinic. The table rename itself
lives in users.0014.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0008_message'),
        ('users', '0014_rename_organization_to_clinic'),
    ]

    operations = [
        migrations.RemoveIndex(model_name='owner', name='patients_ow_organiz_0a9034_idx'),
        migrations.RemoveIndex(model_name='referringclinic', name='patients_re_organiz_c5189e_idx'),

        migrations.RenameField(model_name='owner', old_name='organization', new_name='clinic'),
        migrations.RenameField(model_name='referringclinic', old_name='organization', new_name='clinic'),

        migrations.AddIndex(
            model_name='owner',
            index=models.Index(fields=['clinic', 'last_name'], name='patients_ow_clinic__f2ece9_idx'),
        ),
        migrations.AddIndex(
            model_name='referringclinic',
            index=models.Index(fields=['clinic', 'name'], name='patients_re_clinic__63a2d5_idx'),
        ),
    ]
