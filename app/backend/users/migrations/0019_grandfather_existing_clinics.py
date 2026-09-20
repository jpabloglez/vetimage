"""
Put every existing clinic on an unlimited, non-public "legacy" plan.

Introducing subscription limits must not retroactively take anything away from
customers who predate them. They were sold nothing and agreed to nothing, so
the deploy has to be a no-op for them: same seats, same analyses, same storage.

That is what `legacy` is for — every limit `None`, every feature granted, and
`is_public=False` so it is never offered to anyone new. Clinics created after
this get whichever tier they are put on.

The tiers themselves are seeded by `manage.py seed_plans`, which is idempotent
and owns their definitions. This migration only creates the one plan it needs
to avoid leaving existing rows unassigned, and uses the same values, so running
the command afterwards changes nothing.
"""

from django.db import migrations

LEGACY = {
    'slug': 'legacy',
    'name': 'Legacy',
    'description': 'Grandfathered: predates subscription plans.',
    'seat_limit': None,
    'monthly_analysis_quota': None,
    'storage_bytes': None,
    'features': [
        'owner_portal', 'study_sharing', 'referrals_send',
        'referrals_receive', 'stat_priority', 'api_keys',
    ],
    'is_public': False,
    'sort_order': 90,
}


def grandfather(apps, schema_editor):
    Plan = apps.get_model('users', 'Plan')
    Clinic = apps.get_model('users', 'Clinic')

    legacy, _ = Plan.objects.get_or_create(
        slug=LEGACY['slug'],
        defaults={k: v for k, v in LEGACY.items() if k != 'slug'},
    )
    Clinic.objects.filter(plan__isnull=True).update(plan=legacy)


def ungrandfather(apps, schema_editor):
    """
    Unassign the legacy plan, leaving clinics planless.

    Reversible because it is genuinely harmless: a clinic with no plan is
    treated as unlimited (`users/plans.py`), which is exactly what the legacy
    tier grants. The plan row itself is left alone — deleting it would fail
    against `Clinic.plan`'s PROTECT if anything still points at it, and a
    stray unused row costs nothing.
    """
    Plan = apps.get_model('users', 'Plan')
    Clinic = apps.get_model('users', 'Clinic')

    legacy = Plan.objects.filter(slug=LEGACY['slug']).first()
    if legacy is not None:
        Clinic.objects.filter(plan=legacy).update(plan=None)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_plan_clinic_plan'),
    ]

    operations = [
        migrations.RunPython(grandfather, ungrandfather),
    ]
