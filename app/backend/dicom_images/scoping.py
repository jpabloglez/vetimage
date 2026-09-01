"""
One definition of which DICOM records a user may see.

Studies used to be scoped strictly to their uploader (`uploaded_by=user`) while
every other clinical record — patients, owners, reports, referrals — was scoped
to the organization. The result was incoherent for a shared medical record: a
colleague could open the *report* about Rex's radiograph but not the radiograph
itself.

Studies are now organization-scoped, matching the rest of the clinical record.

The rule is deliberately expressed as `own OR same-organization`, not just
`same-organization`. A user whose UserProfile has no organization — possible
for accounts that never touched an org-scoped endpoint — would otherwise fall
out of the join and lose access to their *own* studies. Keeping the ownership
term makes this a strict superset of the previous behaviour: colleagues gain
visibility, nobody loses it.

There are ~37 scoping sites across views, serializers and services. They all
call through here so the boundary has a single, testable definition.
"""

from django.db.models import Q

from .models import MedicalImage, MedicalSeries, MedicalStudy


def _org_for(user):
    """The user's organization, provisioning one if needed (never raises)."""
    from patients.views import get_or_create_organization
    try:
        return get_or_create_organization(user)
    except Exception:  # pragma: no cover - defensive; scoping must not 500
        return None


def study_scope_q(user, prefix=''):
    """
    A Q filtering to studies *user* may access.

    *prefix* is the path from the model being filtered to MedicalStudy, e.g.
    `'study__'` on MedicalSeries or `'series__study__'` on MedicalImage.
    """
    org = _org_for(user)
    own = Q(**{f'{prefix}uploaded_by': user})
    if org is None:
        return own
    return own | Q(**{f'{prefix}uploaded_by__userprofile__organization': org})


def visible_studies(user):
    """MedicalStudy queryset scoped to *user*'s organization."""
    return MedicalStudy.objects.filter(study_scope_q(user))


def visible_series(user):
    """MedicalSeries queryset scoped to *user*'s organization."""
    return MedicalSeries.objects.filter(study_scope_q(user, prefix='study__'))


def visible_images(user):
    """MedicalImage queryset scoped to *user*'s organization."""
    return MedicalImage.objects.filter(study_scope_q(user, prefix='series__study__'))
