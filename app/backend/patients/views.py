from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import (
    Owner, AnimalPatient, VHSMeasurement,
    ClinicalVisit, VaccinationRecord, WeightRecord, Appointment,
)
from .serializers import (
    OwnerSerializer, AnimalPatientSerializer, AnimalPatientListSerializer,
    VHSMeasurementSerializer,
    ClinicalVisitSerializer, VaccinationRecordSerializer,
    WeightRecordSerializer, AppointmentSerializer,
)


def get_or_create_organization(user):
    """
    Return the user's Organization, creating a default one if needed.

    Freshly registered users get a UserProfile (via signal) but no Organization.
    The veterinary registry is organization-scoped, so we lazily provision a
    clinic organization for the user the first time they use it. Returns None
    only if no UserProfile exists at all (should not happen in practice).
    """
    from users.models import Organization, UserProfile

    profile = getattr(user, 'userprofile', None)
    if profile is None:
        profile, _ = UserProfile.objects.get_or_create(user=user)
    if profile.organization is None:
        org = Organization.objects.create(
            user=user,
            centre=(user.email.split('@')[0] if user.email else 'My Clinic'),
            address='',
            city='',
            billing_address='',
            billing_code='',
        )
        profile.organization = org
        profile.save(update_fields=['organization'])
    return profile.organization


def _check_animal_in_org(animal, user):
    """Raise PermissionDenied if animal does not belong to the user's org."""
    org = get_or_create_organization(user)
    if animal.owner.organization_id != getattr(org, 'id', None):
        raise PermissionDenied('Animal patient is not in your organization.')
    return org


@extend_schema(tags=['Patients'])
class OwnerViewSet(viewsets.ModelViewSet):
    serializer_class = OwnerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    ordering_fields = ['last_name', 'first_name', 'created_at']
    ordering = ['last_name']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return Owner.objects.none()
        return Owner.objects.filter(organization=org).prefetch_related('animals')

    def perform_create(self, serializer):
        org = get_or_create_organization(self.request.user)
        serializer.save(organization=org)


@extend_schema(
    tags=['Patients'],
    parameters=[
        OpenApiParameter('species', OpenApiTypes.STR, description='Filter by species'),
        OpenApiParameter('owner', OpenApiTypes.INT, description='Filter by owner id'),
    ],
)
class AnimalPatientViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'breed', 'microchip_id', 'owner__last_name']
    ordering_fields = ['name', 'species', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return AnimalPatientListSerializer
        return AnimalPatientSerializer

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return AnimalPatient.objects.none()
        qs = AnimalPatient.objects.filter(owner__organization=org).select_related('owner')
        species = self.request.query_params.get('species')
        if species:
            qs = qs.filter(species=species)
        owner_id = self.request.query_params.get('owner')
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
        return qs

    @extend_schema(
        summary='Download pet passport PDF',
        responses={(200, 'application/pdf'): OpenApiTypes.BINARY},
        tags=['Patients'],
    )
    @action(detail=True, methods=['get'], url_path='passport')
    def passport(self, request, pk=None):
        """
        Generate the pet passport / travel health certificate PDF:
        owner, signalment, microchip, vaccination history, vet signature block.
        """
        from django.http import HttpResponse
        from .services.passport_pdf import PassportPDFGenerator

        animal = self.get_object()  # org-scoped via get_queryset
        pdf_buffer = PassportPDFGenerator().generate(animal)

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        safe_name = ''.join(c for c in animal.name if c.isalnum()) or 'pet'
        response['Content-Disposition'] = f'attachment; filename="passport_{safe_name}_{animal.id}.pdf"'
        return response


@extend_schema(
    tags=['VHS'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id')],
)
class VHSMeasurementViewSet(viewsets.ModelViewSet):
    """
    Vertebral Heart Score measurements, scoped to the user's organization
    (via the animal patient's owner). Filter by ?animal=<id>.
    """
    serializer_class = VHSMeasurementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['measured_on', 'created_at', 'vhs']
    ordering = ['-measured_on']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return VHSMeasurement.objects.none()
        qs = VHSMeasurement.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'created_by')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(created_by=self.request.user)


# ---------------------------------------------------------------------------
# Clinical visits
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id')],
)
class ClinicalVisitViewSet(viewsets.ModelViewSet):
    """
    Clinical encounters (SOAP notes + vitals) scoped to the user's organization.
    Filter by ?animal=<id>.
    """
    serializer_class = ClinicalVisitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['visit_date', 'visit_type', 'created_at']
    ordering = ['-visit_date']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return ClinicalVisit.objects.none()
        qs = ClinicalVisit.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'attending_vet', 'created_by')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(
            created_by=self.request.user,
            attending_vet=self.request.user,
        )


# ---------------------------------------------------------------------------
# Vaccination records
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id')],
)
class VaccinationRecordViewSet(viewsets.ModelViewSet):
    """Vaccination history for animal patients. Filter by ?animal=<id>."""
    serializer_class = VaccinationRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['administered_on', 'next_due_on', 'created_at']
    ordering = ['-administered_on']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return VaccinationRecord.objects.none()
        qs = VaccinationRecord.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'administered_by')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(administered_by=self.request.user)


# ---------------------------------------------------------------------------
# Weight records
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id')],
)
class WeightRecordViewSet(viewsets.ModelViewSet):
    """Time-series weight measurements. Filter by ?animal=<id>."""
    serializer_class = WeightRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['measured_on', 'weight_kg', 'created_at']
    ordering = ['-measured_on']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return WeightRecord.objects.none()
        qs = WeightRecord.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'recorded_by')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(recorded_by=self.request.user)


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

@extend_schema(
    tags=['Patients'],
    parameters=[
        OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id'),
        OpenApiParameter('status', OpenApiTypes.STR, description='Filter by appointment status'),
        OpenApiParameter('date_from', OpenApiTypes.DATE, description='Filter scheduled_at >= date_from'),
        OpenApiParameter('date_to', OpenApiTypes.DATE, description='Filter scheduled_at <= date_to'),
    ],
)
class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Clinic appointments scoped to the user's organization.
    Filter by ?animal=<id>&status=pending&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD.
    """
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['scheduled_at', 'status', 'created_at']
    ordering = ['scheduled_at']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return Appointment.objects.none()
        qs = Appointment.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient__owner', 'attending_vet', 'created_by')

        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)

        appt_status = self.request.query_params.get('status')
        if appt_status:
            qs = qs.filter(status=appt_status)

        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(scheduled_at__date__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(scheduled_at__date__lte=date_to)

        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark appointment completed and auto-create a linked ClinicalVisit."""
        appt = self.get_object()
        if appt.status == 'completed':
            return Response({'error': 'Appointment is already completed.'}, status=status.HTTP_400_BAD_REQUEST)

        visit = ClinicalVisit.objects.create(
            animal_patient=appt.animal_patient,
            visit_date=appt.scheduled_at,
            visit_type=appt.appointment_type,
            attending_vet=appt.attending_vet,
            created_by=request.user,
        )
        appt.status = 'completed'
        appt.linked_visit = visit
        appt.save(update_fields=['status', 'linked_visit'])
        return Response({'visit_id': visit.id}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# P2 ViewSets: Prescription, AllergyRecord, ClinicalPhoto, LabResult
# All follow the same org-scoping pattern as Phase 1 ViewSets.
# ---------------------------------------------------------------------------

from .models import Prescription, AllergyRecord, ClinicalPhoto, LabResult
from .serializers import (
    PrescriptionSerializer, AllergyRecordSerializer,
    ClinicalPhotoSerializer, LabResultSerializer,
)


@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id')],
)
class PrescriptionViewSet(viewsets.ModelViewSet):
    """Prescription history for animal patients. Filter by ?animal=<id>."""
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['prescribed_on', 'medication_name', 'created_at']
    ordering = ['-prescribed_on']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return Prescription.objects.none()
        qs = Prescription.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'prescribed_by', 'visit')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(prescribed_by=self.request.user)


@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id')],
)
class AllergyRecordViewSet(viewsets.ModelViewSet):
    """Allergy / adverse reaction records. Filter by ?animal=<id>."""
    serializer_class = AllergyRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering = ['-severity', 'allergen']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return AllergyRecord.objects.none()
        qs = AllergyRecord.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'recorded_by')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(recorded_by=self.request.user)


@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id')],
)
class ClinicalPhotoViewSet(viewsets.ModelViewSet):
    """Clinical photos for animal patients. Filter by ?animal=<id>."""
    serializer_class = ClinicalPhotoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['taken_on', 'created_at']
    ordering = ['-taken_on']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return ClinicalPhoto.objects.none()
        qs = ClinicalPhoto.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'visit', 'taken_by')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(taken_by=self.request.user)


@extend_schema(
    tags=['Patients'],
    parameters=[
        OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id'),
        OpenApiParameter('result_type', OpenApiTypes.STR, description='Filter by result type'),
    ],
)
class LabResultViewSet(viewsets.ModelViewSet):
    """Lab result panels for animal patients. Filter by ?animal=<id>&result_type=hematology."""
    serializer_class = LabResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['result_date', 'result_type', 'created_at']
    ordering = ['-result_date']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return LabResult.objects.none()
        qs = LabResult.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'visit', 'requested_by')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        result_type = self.request.query_params.get('result_type')
        if result_type:
            qs = qs.filter(result_type=result_type)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(requested_by=self.request.user)

    def _import_parsed(self, request, parsed):
        """Create a LabResult from a parser result dict (shared by both importers)."""
        animal_id = request.data.get('animal_patient_id')
        if not animal_id:
            return Response({'error': 'animal_patient_id is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            animal = AnimalPatient.objects.get(pk=animal_id)
        except AnimalPatient.DoesNotExist:
            return Response({'error': 'Animal patient not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        _check_animal_in_org(animal, request.user)

        result = LabResult.objects.create(
            animal_patient=animal,
            requested_by=request.user,
            result_type=parsed['result_type'],
            panel_name=parsed['panel_name'],
            result_date=parsed['result_date'],
            result_data=parsed['result_data'],
            lab_name=request.data.get('lab_name') or parsed['lab_name'],
        )
        serializer = self.get_serializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary='Import an HL7 v2 ORU^R01 lab message',
        tags=['Patients'],
    )
    @action(detail=False, methods=['post'], url_path='import-hl7')
    def import_hl7(self, request):
        """Body: {animal_patient_id, message: <raw HL7 ORU text>, lab_name?}."""
        from .services.lab_import import parse_hl7_oru
        try:
            parsed = parse_hl7_oru(request.data.get('message', ''))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._import_parsed(request, parsed)

    @extend_schema(
        summary='Import a FHIR R4 DiagnosticReport',
        tags=['Patients'],
    )
    @action(detail=False, methods=['post'], url_path='import-fhir')
    def import_fhir(self, request):
        """Body: {animal_patient_id, report: <FHIR DiagnosticReport JSON>, lab_name?}."""
        from .services.lab_import import parse_fhir_diagnostic_report
        try:
            parsed = parse_fhir_diagnostic_report(request.data.get('report'))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._import_parsed(request, parsed)


# ---------------------------------------------------------------------------
# P3 ViewSet: ReproductiveEvent
# ---------------------------------------------------------------------------

from .models import ReproductiveEvent
from .serializers import ReproductiveEventSerializer


@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal patient id')],
)
class ReproductiveEventViewSet(viewsets.ModelViewSet):
    """Reproductive history events for animal patients. Filter by ?animal=<id>."""
    serializer_class = ReproductiveEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['event_date', 'event_type', 'created_at']
    ordering = ['-event_date']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return ReproductiveEvent.objects.none()
        qs = ReproductiveEvent.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'recorded_by')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        _check_animal_in_org(animal, self.request.user)
        serializer.save(recorded_by=self.request.user)


# ---------------------------------------------------------------------------
# Referral network (#24)
# ---------------------------------------------------------------------------
from rest_framework.views import APIView  # noqa: E402
from .models import ReferringClinic, ReferralPackage  # noqa: E402
from .serializers import (  # noqa: E402
    ReferringClinicSerializer, ReferralPackageSerializer,
    PublicReferralPackageSerializer,
)


@extend_schema(tags=['Patients'])
class ReferringClinicViewSet(viewsets.ModelViewSet):
    """Org-scoped address book of partner/referring clinics."""
    serializer_class = ReferringClinicSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'contact_name', 'contact_email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return ReferringClinic.objects.none()
        return ReferringClinic.objects.filter(organization=org)

    def perform_create(self, serializer):
        org = get_or_create_organization(self.request.user)
        serializer.save(organization=org, created_by=self.request.user)


@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal id')],
)
class ReferralPackageViewSet(viewsets.ModelViewSet):
    """
    Token-gated referral bundles (study + report + history snapshot). Filter by
    ?animal=<id>. The public landing page lives at /api/patients/referrals/<token>/.
    """
    serializer_class = ReferralPackageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at', 'urgency']
    ordering = ['-created_at']

    def get_queryset(self):
        org = get_or_create_organization(self.request.user)
        if org is None:
            return ReferralPackage.objects.none()
        qs = ReferralPackage.objects.filter(
            animal_patient__owner__organization=org
        ).select_related('animal_patient', 'referring_clinic', 'study', 'report')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        org = _check_animal_in_org(animal, self.request.user)
        clinic = serializer.validated_data.get('referring_clinic')
        if clinic and clinic.organization_id != getattr(org, 'id', None):
            raise PermissionDenied('Referring clinic is not in your organization.')
        serializer.save(created_by=self.request.user)


@extend_schema(
    summary='Public specialist view of a referral package',
    description='Read-only, sanitised referral bundle via its unguessable token. '
                'No authentication required.',
    tags=['Patients'],
    auth=[],
)
class PublicReferralPackageView(APIView):
    """Unauthenticated, token-gated referral landing page for the receiving vet."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, token):
        from django.db.models import F
        try:
            pkg = ReferralPackage.objects.select_related(
                'animal_patient', 'referring_clinic', 'study', 'report'
            ).get(token=token)
        except (ReferralPackage.DoesNotExist, ValueError, Exception):
            return Response({'error': 'Referral not found'}, status=status.HTTP_404_NOT_FOUND)
        if not pkg.is_valid():
            return Response({'error': 'Referral link has expired'}, status=status.HTTP_404_NOT_FOUND)
        ReferralPackage.objects.filter(pk=pkg.pk).update(access_count=F('access_count') + 1)
        pkg.refresh_from_db(fields=['access_count'])
        return Response(PublicReferralPackageSerializer(pkg).data)


# ---------------------------------------------------------------------------
# Owner ↔ clinic messaging (#22)
# ---------------------------------------------------------------------------
from .models import Message  # noqa: E402
from .serializers import MessageSerializer  # noqa: E402
from users.models import PET_OWNER_ROLE  # noqa: E402


@extend_schema(
    tags=['Patients'],
    parameters=[OpenApiParameter('animal', OpenApiTypes.INT, description='Filter by animal id')],
)
class MessageViewSet(viewsets.ModelViewSet):
    """
    Owner↔clinic message thread for an animal (`?animal=<id>`). Accessible to
    clinic staff (org-scoped) and the pet owner (email-scoped). Messages are
    append-only — no edit/delete — so the thread stays auditable.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def _is_owner(self):
        return getattr(self.request.user, 'role', None) == PET_OWNER_ROLE

    def get_queryset(self):
        user = self.request.user
        if self._is_owner():
            qs = Message.objects.filter(animal_patient__owner__email__iexact=user.email)
        else:
            org = get_or_create_organization(user)
            if org is None:
                return Message.objects.none()
            qs = Message.objects.filter(animal_patient__owner__organization=org)
        qs = qs.select_related('animal_patient', 'animal_patient__owner', 'sender')
        animal_id = self.request.query_params.get('animal')
        if animal_id:
            qs = qs.filter(animal_patient_id=animal_id)
        return qs

    def _check_access(self, animal):
        user = self.request.user
        if self._is_owner():
            if (animal.owner.email or '').lower() != (user.email or '').lower():
                raise PermissionDenied('This animal is not associated with your account.')
        else:
            _check_animal_in_org(animal, user)

    def perform_create(self, serializer):
        animal = serializer.validated_data['animal_patient']
        self._check_access(animal)
        msg = serializer.save(sender=self.request.user, from_owner=self._is_owner())
        self._notify_counterpart(msg)

    def _notify_counterpart(self, msg):
        """Notify the other side of the thread that a new message arrived."""
        from credentials.models import Notification
        from users.models import User
        animal = msg.animal_patient
        if msg.from_owner:
            # Owner messaged the clinic → notify the org's owning staff user.
            org = animal.owner.organization
            recipient = getattr(org, 'user', None)
            link = f'/patients?animal={animal.id}'
            text = f"New message from {animal.owner} about {animal.name}."
        else:
            # Clinic messaged the owner → notify the owner's portal account.
            recipient = User.objects.filter(
                email__iexact=animal.owner.email, role=PET_OWNER_ROLE,
            ).first()
            link = '/portal'
            text = f"New message from your clinic about {animal.name}."
        if recipient and recipient != msg.sender:
            Notification.objects.create(
                user=recipient, message=text, notification_type='info', link=link,
            )

    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Mark the other side's messages for an animal as read."""
        animal_id = request.data.get('animal')
        if not animal_id:
            return Response({'error': 'animal is required.'}, status=status.HTTP_400_BAD_REQUEST)
        # Owners read clinic messages (from_owner=False); staff read owner messages.
        other_side_from_owner = not self._is_owner()
        updated = self.get_queryset().filter(
            animal_patient_id=animal_id, from_owner=other_side_from_owner, is_read=False,
        ).update(is_read=True)
        return Response({'marked_read': updated})
