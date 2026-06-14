"""
Seed breed-specific VHS reference ranges.

VHS (Vertebral Heart Score) population norms are breed-dependent. These widely
cited ranges refine the species-wide defaults for breeds known to sit outside
the general population range. Reference only — never a diagnosis.

Usage:
    python manage.py seed_breed_references
"""
from django.core.management.base import BaseCommand
from patients.models import BreedReference


# (species, breed_pattern, metric, low, high, source)
# breed_pattern is a case-insensitive substring of the animal's breed.
BREED_VHS_REFERENCES = [
    # Species-wide defaults (mirror VHS_REFERENCE; provide a DB-backed fallback).
    ('canine', '', 'vhs', 8.5, 10.6, 'Buchanan & Bücheler 1995 (general canine)'),
    ('feline', '', 'vhs', 6.7, 8.1, 'Litster & Buchanan 2000 (general feline)'),
    # Breeds with documented higher normal VHS.
    ('canine', 'Boxer', 'vhs', 9.8, 11.6, 'Lamb et al. 2001'),
    ('canine', 'Labrador', 'vhs', 9.7, 11.7, 'Bavegems et al. 2005'),
    ('canine', 'Cavalier King Charles', 'vhs', 9.9, 11.7, 'Lamb et al. 2001'),
    ('canine', 'Whippet', 'vhs', 10.0, 11.8, 'Bavegems et al. 2005'),
    ('canine', 'Greyhound', 'vhs', 10.5, 11.5, 'Marin et al. 2007'),
    ('canine', 'Yorkshire', 'vhs', 9.0, 10.5, 'Ghadiri et al. 2008'),
    # Breeds with documented lower normal VHS.
    ('canine', 'Dachshund', 'vhs', 9.0, 10.4, 'Lamb et al. 2001'),
]


class Command(BaseCommand):
    help = 'Seed breed-specific VHS reference ranges (idempotent).'

    def handle(self, *args, **options):
        created, updated = 0, 0
        for species, pattern, metric, low, high, source in BREED_VHS_REFERENCES:
            obj, was_created = BreedReference.objects.update_or_create(
                species=species, breed_pattern=pattern, metric=metric,
                defaults={'low': low, 'high': high, 'source': source},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f'Breed references seeded: {created} created, {updated} updated '
            f'({BreedReference.objects.count()} total).'
        ))
