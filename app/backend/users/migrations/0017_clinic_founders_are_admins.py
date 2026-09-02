"""
Make existing clinic founders administrators of their own clinic.

Clinics were provisioned without granting the founder any administrative role,
so on a database created before this migration the person who created a clinic
cannot invite anyone into it — the clinic has no administrator at all.
`get_or_create_clinic` now grants the role at provisioning time; this brings
existing rows in line.

Scope is deliberately narrow: only a user who both *created* a clinic
(`Clinic.user`) and is currently a member of that same clinic. A founder who
has since moved to another clinic is left alone, as is every user who merely
joined one.
"""

from django.db import migrations

CLINIC_ADMIN_ROLE = 3
VETERINARIAN_ROLE = 1


def promote_founders(apps, schema_editor):
    Clinic = apps.get_model('users', 'Clinic')

    for clinic in Clinic.objects.select_related('user').all():
        founder = clinic.user
        if founder is None or founder.role != VETERINARIAN_ROLE:
            continue

        profile = getattr(founder, 'userprofile', None)
        if profile is None or profile.clinic_id != clinic.id:
            continue

        founder.role = CLINIC_ADMIN_ROLE
        founder.save(update_fields=['role'])


def demote_founders(apps, schema_editor):
    """
    Deliberately a no-op.

    Roles are also set by hand and by invitation, so there is no way to tell
    which Clinic Admin this migration created. Reversing it would revoke access
    from people who were always meant to have it.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_clinic_invitation'),
    ]

    operations = [
        migrations.RunPython(promote_founders, demote_founders),
    ]
