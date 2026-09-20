"""
Seed the subscription tiers.

Idempotent, like the other seed commands: safe to re-run after a deploy, and it
updates an existing tier in place rather than creating a duplicate.

The numbers here are the opening proposal, not a pricing decision — they are
meant to be edited. What is *not* arbitrary is the shape: seats are what a
practice budgets against, AI analyses track the real marginal cost, and storage
stops one practice's decade of archives becoming everyone's problem.
"""

from django.core.management.base import BaseCommand

from users.models import Plan

GB = 1024 ** 3

F = Plan  # shorthand for the feature constants below

PLANS = [
    {
        'slug': 'solo',
        'name': 'Solo',
        'description': 'A single vet or a two-person practice.',
        'seat_limit': 2,
        'monthly_analysis_quota': 20,
        'storage_bytes': 50 * GB,
        'features': [],
        'sort_order': 10,
    },
    {
        'slug': 'practice',
        'name': 'Practice',
        'description': 'A working small-animal practice.',
        'seat_limit': 10,
        'monthly_analysis_quota': 200,
        'storage_bytes': 500 * GB,
        'features': [
            F.FEATURE_OWNER_PORTAL,
            F.FEATURE_STUDY_SHARING,
            F.FEATURE_REFERRALS_SEND,
        ],
        'sort_order': 20,
    },
    {
        'slug': 'referral',
        'name': 'Referral',
        'description': 'Referral centres and specialists taking cases in.',
        'seat_limit': None,
        'monthly_analysis_quota': 1000,
        'storage_bytes': 2048 * GB,
        'features': [
            F.FEATURE_OWNER_PORTAL,
            F.FEATURE_STUDY_SHARING,
            F.FEATURE_REFERRALS_SEND,
            F.FEATURE_REFERRALS_RECEIVE,
            F.FEATURE_STAT_PRIORITY,
            F.FEATURE_API_KEYS,
        ],
        'sort_order': 30,
    },
    {
        # Everything unlimited, and not offered to anyone new. Clinics that
        # existed before plans were sold nothing and agreed to nothing, so
        # introducing limits must not retroactively take anything away from
        # them. Migration users.0018 puts them here.
        'slug': 'legacy',
        'name': 'Legacy',
        'description': 'Grandfathered: predates subscription plans.',
        'seat_limit': None,
        'monthly_analysis_quota': None,
        'storage_bytes': None,
        'features': [
            F.FEATURE_OWNER_PORTAL,
            F.FEATURE_STUDY_SHARING,
            F.FEATURE_REFERRALS_SEND,
            F.FEATURE_REFERRALS_RECEIVE,
            F.FEATURE_STAT_PRIORITY,
            F.FEATURE_API_KEYS,
        ],
        'is_public': False,
        'sort_order': 90,
    },
]


class Command(BaseCommand):
    help = 'Create or update the subscription plans.'

    def handle(self, *args, **options):
        created_count = 0
        for spec in PLANS:
            spec = dict(spec)
            slug = spec.pop('slug')
            _, created = Plan.objects.update_or_create(slug=slug, defaults=spec)
            created_count += int(created)
            self.stdout.write(
                f'  {"created" if created else "updated"}  {slug}'
            )
        self.stdout.write(self.style.SUCCESS(
            f'{len(PLANS)} plans seeded ({created_count} new).'
        ))
