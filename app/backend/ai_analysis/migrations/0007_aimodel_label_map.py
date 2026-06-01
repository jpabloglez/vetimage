from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_analysis', '0006_aimodel_use_orchestrator'),
    ]

    operations = [
        migrations.AddField(
            model_name='aimodel',
            name='label_map',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Mapping from integer label ID to anatomy name "
                    "(e.g. {'1': 'liver', '2': 'spleen'}). "
                    "Used for DICOM SEG creation and structured report generation."
                ),
            ),
        ),
    ]
