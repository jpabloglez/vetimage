"""
Pet-owner portal (#21).

Owner accounts are ordinary `users.User` rows with role == PET_OWNER_ROLE,
linked to their clinical `Owner` record(s) by a case-insensitive email match.
Because the same person may be a client at more than one clinic (one `Owner`
row per organisation, all sharing the email), the portal aggregates across all
matching `Owner` records. Owners only ever see their own pets and the reports a
clinic has explicitly approved + shared.
"""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from users.models import PET_OWNER_ROLE
from .models import AnimalPatient


class IsPetOwner(permissions.BasePermission):
    """Allow only authenticated pet-owner accounts."""
    message = 'Pet-owner account required.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'role', None) == PET_OWNER_ROLE)


def _owner_animals(user):
    """Animals across every Owner record whose email matches the account."""
    return AnimalPatient.objects.filter(
        owner__email__iexact=user.email
    ).select_related('owner', 'owner__organization').order_by('name')


def _pet_payload(animal):
    today = timezone.now().date()
    now = timezone.now()
    org = animal.owner.organization
    vaccinations = [
        {
            'vaccine_name': v.vaccine_name,
            'administered_on': v.administered_on.isoformat(),
            'next_due_on': v.next_due_on.isoformat() if v.next_due_on else None,
            'overdue': bool(v.next_due_on and v.next_due_on < today),
        }
        for v in animal.vaccinations.all().order_by('-administered_on')[:10]
    ]
    appointments = [
        {
            'appointment_type': a.appointment_type,
            'scheduled_at': a.scheduled_at.isoformat(),
            'status': a.status,
        }
        for a in animal.appointments.filter(
            scheduled_at__gte=now, status__in=['pending', 'confirmed'],
        ).order_by('scheduled_at')[:5]
    ]
    return {
        'id': animal.id,
        'name': animal.name,
        'species': animal.get_species_display(),
        'breed': animal.breed,
        'sex': animal.get_sex_display() if animal.sex else '',
        'date_of_birth': animal.date_of_birth.isoformat() if animal.date_of_birth else None,
        'profile_photo': animal.profile_photo.url if animal.profile_photo else None,
        'clinic': org.centre if org else None,
        'vaccinations': vaccinations,
        'upcoming_appointments': appointments,
    }


@extend_schema(
    summary='Pet-owner portal dashboard',
    description='Aggregated view for the authenticated pet owner: their pets '
                '(with vaccination status and upcoming appointments) and the '
                'reports their clinic has approved and shared.',
    responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    tags=['Owner Portal'],
)
class OwnerPortalDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPetOwner]

    def get(self, request):
        from reports.models import Report

        animals = list(_owner_animals(request.user))
        pets = [_pet_payload(a) for a in animals]

        shared = Report.objects.filter(
            study__animal_patient__owner__email__iexact=request.user.email,
            share_token__isnull=False,
            approved_at__isnull=False,
        ).select_related('study', 'study__animal_patient').order_by('-approved_at')
        shared_reports = [
            {
                'title': r.title,
                'pet_name': r.study.animal_patient.name if r.study and r.study.animal_patient else '',
                'approved_at': r.approved_at.isoformat() if r.approved_at else None,
                'share_path': f'/shared/{r.share_token}',
            }
            for r in shared
        ]

        return Response({
            'owner': {'email': request.user.email, 'pet_count': len(pets)},
            'pets': pets,
            'shared_reports': shared_reports,
        })


@extend_schema(
    summary='Provision a pet-owner portal account',
    description='Clinic-side action: create a portal login (role=Pet Owner) for '
                'an existing Owner record, using the Owner email. Returns 400 if '
                'an account with that email already exists.',
    request=OpenApiTypes.OBJECT,
    responses={201: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    tags=['Owner Portal'],
)
class OwnerAccountProvisionView(APIView):
    """Clinic staff create an initial portal password for one of their owners."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, owner_id):
        from users.models import User
        from .models import Owner
        from .views import get_or_create_organization

        org = get_or_create_organization(request.user)
        try:
            owner = Owner.objects.get(id=owner_id, organization=org)
        except Owner.DoesNotExist:
            return Response({'error': 'Owner not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not owner.email:
            return Response({'error': 'Owner has no email on file.'}, status=status.HTTP_400_BAD_REQUEST)

        password = request.data.get('password')
        if not password or len(password) < 8:
            return Response({'error': 'A password of at least 8 characters is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=owner.email).exists():
            return Response({'error': 'An account with this email already exists.'},
                            status=status.HTTP_400_BAD_REQUEST)

        account = User.objects.create_user(email=owner.email, password=password, role=PET_OWNER_ROLE)
        return Response({'id': account.id, 'email': account.email, 'role': account.role},
                        status=status.HTTP_201_CREATED)
