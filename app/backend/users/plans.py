"""
Plan limits: what a clinic is currently using, and whether it may do more.

One module so there is one answer. A limit checked in the view and displayed
from a different query drifts the moment either changes, and the failure mode
is the worst kind — the UI says a clinic has room, the API refuses, and nobody
can tell which is lying.

**Two rules shape everything here.**

*Limits apply to creation, never retroactively.* A clinic over its seat count
or past its quota is blocked from adding more; it is never cut off from records
it already has. Patient history is a clinical and legal obligation, and making
it contingent on a subscription is not a product decision anyone should make
casually.

*Only active members occupy a seat.* Revoking access (`users/views_clinic.py`)
deactivates rather than deletes, so counting every row would mean offboarding a
vet never frees the seat you are paying for.
"""

from django.db.models import Sum
from django.utils import timezone

from .models import Plan

#: Returned instead of a number when no limit applies.
UNLIMITED = None


def plan_for(clinic):
    """
    The clinic's plan, or None when it has none.

    None is treated as unlimited rather than as zero. A clinic that predates
    plans, or one a migration has not reached, must keep working.
    """
    return getattr(clinic, 'plan', None)


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

def seats_used(clinic) -> int:
    """Active members. Revoked accounts keep their records but not their seat."""
    from .models import UserProfile

    return UserProfile.objects.filter(
        clinic=clinic, user__is_active=True,
    ).count()


def pending_invitations(clinic) -> int:
    """
    Invitations sent, not yet accepted, and still live.

    Mirrors `ClinicInvitation.is_pending`, which is a Python property and so
    cannot be filtered on in SQL.
    """
    from .models import ClinicInvitation

    return ClinicInvitation.objects.filter(
        clinic=clinic,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).count()


def seats_occupied(clinic) -> int:
    """
    Seats actually spoken for: active members plus live invitations.

    **Both the usage report and the seat check must use this.** They diverged
    once — the panel counted only members while the check also counted pending
    invitations, so it showed a free seat while the API refused to fill it.
    A limit displayed from a different query than the one enforcing it is worse
    than no display at all, because nobody can tell which is lying.
    """
    return seats_used(clinic) + pending_invitations(clinic)


def month_start(now=None):
    """
    First instant of the current calendar month.

    Calendar month, not a rolling 30 days: a quota people can reason about
    ("resets on the 1st") beats one that is technically smoother.
    """
    now = now or timezone.now()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def analyses_this_month(clinic, now=None) -> int:
    from ai_analysis.models import AnalysisTask

    return AnalysisTask.objects.filter(
        created_by__userprofile__clinic=clinic,
        created_at__gte=month_start(now),
    ).count()


def storage_used(clinic) -> int:
    """Total stored image bytes for the clinic, in bytes."""
    from dicom_images.models import MedicalImage

    total = MedicalImage.objects.filter(
        series__study__uploaded_by__userprofile__clinic=clinic,
    ).aggregate(total=Sum('file_size_bytes'))['total']
    return total or 0


def usage(clinic) -> dict:
    """
    Everything the UI needs to show usage against limits, in one shape.

    `limit` is None where nothing applies, so a caller renders "unlimited"
    rather than having to know that some sentinel number means it.
    """
    plan = plan_for(clinic)

    def entry(used, limit):
        return {
            'used': used,
            'limit': limit,
            'remaining': None if limit is None else max(limit - used, 0),
            'exceeded': limit is not None and used >= limit,
        }

    return {
        'plan': None if plan is None else {
            'slug': plan.slug,
            'name': plan.name,
            'features': list(plan.features or []),
        },
        'seats': {
            **entry(seats_occupied(clinic), plan.seat_limit if plan else None),
            # Broken out so the panel can say *why* a seat is taken, rather
            # than showing a number the admin cannot reconcile with the roster.
            'members': seats_used(clinic),
            'pending_invitations': pending_invitations(clinic),
        },
        'analyses': entry(
            analyses_this_month(clinic),
            plan.monthly_analysis_quota if plan else None,
        ),
        'storage': entry(storage_used(clinic), plan.storage_bytes if plan else None),
    }


# ---------------------------------------------------------------------------
# Checks — each returns None to allow, or a reason string to refuse
# ---------------------------------------------------------------------------

def _refusal(used, limit, what, advice):
    if limit is None or used < limit:
        return None
    return (
        f'Your plan includes {limit} {what}, and {used} are in use. '
        f'{advice}'
    )


def seat_refusal(clinic):
    """
    Why a clinic may not add another member, or None.

    Pending invitations count against the limit. Without that a clinic could
    invite its way past the seat count and only discover it as people started
    accepting — which is the worst possible moment to find out, because the
    invitation has already been sent and someone has to be turned away.
    """
    plan = plan_for(clinic)
    if plan is None or plan.seat_limit is None:
        return None
    used = seats_occupied(clinic)
    return _refusal(
        used, plan.seat_limit, 'members',
        'Revoke access for someone who has left, or move to a larger plan. '
        'Invitations that have been sent but not accepted also count.',
    )


def analysis_refusal(clinic):
    """Why a clinic may not start another analysis this month, or None."""
    plan = plan_for(clinic)
    if plan is None or plan.monthly_analysis_quota is None:
        return None
    used = analyses_this_month(clinic)
    return _refusal(
        used, plan.monthly_analysis_quota, 'AI analyses per month',
        'The quota resets on the 1st. Existing results stay available.',
    )


def feature_refusal(clinic, feature: str):
    """Why a clinic may not use a gated feature, or None."""
    plan = plan_for(clinic)
    if plan is None or plan.grants(feature):
        return None
    label = dict(Plan.FEATURE_CHOICES).get(feature, feature)
    return f'{label} is not included in the {plan.name} plan.'
