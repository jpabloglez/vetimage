from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import (
    Owner, AnimalPatient, VHSMeasurement, VHS_REFERENCE,
    ClinicalVisit, VaccinationRecord, WeightRecord, Appointment,
    ReferringClinic, ReferralPackage, Message,
)


class OwnerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = ['id', 'first_name', 'last_name', 'email', 'phone']


class AnimalPatientListSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = AnimalPatient
        fields = ['id', 'name', 'species', 'breed', 'sex', 'owner_name', 'profile_photo']

    @extend_schema_field(OpenApiTypes.STR)
    def get_owner_name(self, obj):
        return str(obj.owner)


class AnimalPatientSerializer(serializers.ModelSerializer):
    owner = OwnerSummarySerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=Owner.objects.all(), source='owner', write_only=True
    )
    studies = serializers.SerializerMethodField()
    vhs_trend = serializers.SerializerMethodField()
    weight_trend = serializers.SerializerMethodField()
    vaccinations = serializers.SerializerMethodField()
    upcoming_appointments = serializers.SerializerMethodField()
    visits_count = serializers.IntegerField(source='visits.count', read_only=True)

    class Meta:
        model = AnimalPatient
        fields = [
            'id', 'owner', 'owner_id', 'name', 'species', 'breed',
            'date_of_birth', 'sex', 'weight_kg', 'microchip_id', 'color',
            'profile_photo',
            'insurance_provider', 'insurance_policy_number', 'insurance_expiry',
            'visits_count',
            'studies', 'vhs_trend', 'weight_trend',
            'vaccinations', 'upcoming_appointments',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_weight_kg(self, value):
        if value is not None and (value <= 0 or value >= 2000):
            raise serializers.ValidationError('Weight must be between 0 and 2000 kg.')
        return value

    def validate_date_of_birth(self, value):
        from django.utils import timezone
        if value and value > timezone.now().date():
            raise serializers.ValidationError('Date of birth cannot be in the future.')
        return value

    def validate_microchip_id(self, value):
        import re
        if not value:
            return value
        if not (re.fullmatch(r'\d{15}', value) or re.fullmatch(r'[A-Za-z0-9]{9,20}', value)):
            raise serializers.ValidationError(
                'Microchip should be 15 digits (ISO) or a 9–20 character alphanumeric ID.'
            )
        request = self.context.get('request')
        org = None
        if request is not None:
            try:
                from .views import get_or_create_organization
                org = get_or_create_organization(request.user)
            except Exception:
                org = None
        if org is not None:
            qs = AnimalPatient.objects.filter(owner__organization=org, microchip_id=value)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    'Another patient in your clinic already has this microchip ID.'
                )
        return value

    @extend_schema_field(serializers.ListSerializer(child=serializers.DictField()))
    def get_vhs_trend(self, obj):
        measurements = obj.vhs_measurements.all().order_by('measured_on')
        return [
            {
                'id': m.id,
                'measured_on': m.measured_on.isoformat() if m.measured_on else None,
                'vhs': float(m.vhs),
                'long_axis_vertebrae': float(m.long_axis_vertebrae),
                'short_axis_vertebrae': float(m.short_axis_vertebrae),
                'interpretation': m.interpretation,
                'method': m.method,
                'notes': m.notes,
            }
            for m in measurements
        ]

    @extend_schema_field(serializers.ListSerializer(child=serializers.DictField()))
    def get_weight_trend(self, obj):
        records = obj.weight_records.all().order_by('measured_on')
        return [
            {
                'id': r.id,
                'measured_on': r.measured_on.isoformat(),
                'weight_kg': float(r.weight_kg),
                'bcs': r.bcs,
                'notes': r.notes,
            }
            for r in records
        ]

    @extend_schema_field(serializers.ListSerializer(child=serializers.DictField()))
    def get_vaccinations(self, obj):
        records = obj.vaccinations.all().order_by('-administered_on')
        return [
            {
                'id': r.id,
                'vaccine_name': r.vaccine_name,
                'administered_on': r.administered_on.isoformat(),
                'next_due_on': r.next_due_on.isoformat() if r.next_due_on else None,
                'batch_number': r.batch_number,
                'notes': r.notes,
            }
            for r in records
        ]

    @extend_schema_field(serializers.ListSerializer(child=serializers.DictField()))
    def get_upcoming_appointments(self, obj):
        from django.utils import timezone
        appts = obj.appointments.filter(
            scheduled_at__gte=timezone.now(),
            status__in=['pending', 'confirmed'],
        ).order_by('scheduled_at')[:3]
        return [
            {
                'id': a.id,
                'appointment_type': a.appointment_type,
                'scheduled_at': a.scheduled_at.isoformat(),
                'status': a.status,
                'duration_minutes': a.duration_minutes,
            }
            for a in appts
        ]

    @extend_schema_field(serializers.ListSerializer(child=serializers.DictField()))
    def get_studies(self, obj):
        studies = obj.studies.all().order_by('-study_date', '-uploaded_at')
        return [
            {
                'study_instance_uid': s.study_instance_uid,
                'study_description': s.study_description,
                'study_date': s.study_date,
            }
            for s in studies
        ]


class VHSMeasurementSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    vhs = serializers.DecimalField(max_digits=4, decimal_places=1, read_only=True)
    interpretation = serializers.CharField(read_only=True)
    reference_range = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = VHSMeasurement
        fields = [
            'id', 'animal_patient_id', 'study_instance_uid', 'sop_instance_uid',
            'measured_on', 'long_axis_vertebrae', 'short_axis_vertebrae', 'vhs',
            'method', 'landmark_points', 'notes', 'interpretation', 'reference_range',
            'created_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = ['vhs', 'created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_reference_range(self, obj):
        # Breed-specific range (if any) wins over the species-wide default.
        from .models import BreedReference
        ref = BreedReference.lookup(obj.animal_patient.species, obj.animal_patient.breed, 'vhs')
        return ref or VHS_REFERENCE.get(obj.animal_patient.species)


class OwnerSerializer(serializers.ModelSerializer):
    animals = AnimalPatientListSerializer(many=True, read_only=True)
    animals_count = serializers.IntegerField(source='animals.count', read_only=True)

    class Meta:
        model = Owner
        fields = [
            'id', 'organization', 'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'country', 'animals_count', 'animals',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['organization', 'created_at', 'updated_at']

    def validate_country(self, value):
        """Harmonise to an ISO 3166-1 alpha-2 code (uppercased); blank allowed."""
        import re
        if not value:
            return value
        if not re.fullmatch(r'[A-Za-z]{2}', value):
            raise serializers.ValidationError(
                'Country must be a 2-letter ISO country code (e.g. US, ES, BR).'
            )
        return value.upper()


# ---------------------------------------------------------------------------
# Clinical visit
# ---------------------------------------------------------------------------

class ClinicalVisitSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    attending_vet_email = serializers.EmailField(
        source='attending_vet.email', read_only=True,
    )

    class Meta:
        model = ClinicalVisit
        fields = [
            'id', 'animal_patient_id', 'visit_date', 'visit_type',
            'attending_vet_email', 'chief_complaint',
            'subjective', 'objective', 'assessment', 'plan',
            'weight_kg', 'temperature_celsius', 'heart_rate_bpm', 'respiratory_rate',
            'linked_study', 'linked_report', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_weight_kg(self, value):
        if value is not None and (value <= 0 or value >= 2000):
            raise serializers.ValidationError('Weight must be between 0 and 2000 kg.')
        return value

    def validate_temperature_celsius(self, value):
        if value is not None and not (30 < float(value) < 45):
            raise serializers.ValidationError('Temperature must be between 30 and 45 °C.')
        return value

    def validate_heart_rate_bpm(self, value):
        if value is not None and not (1 <= value <= 400):
            raise serializers.ValidationError('Heart rate must be between 1 and 400 bpm.')
        return value

    def validate_respiratory_rate(self, value):
        if value is not None and not (1 <= value <= 100):
            raise serializers.ValidationError('Respiratory rate must be between 1 and 100.')
        return value


# ---------------------------------------------------------------------------
# Vaccination record
# ---------------------------------------------------------------------------

class VaccinationRecordSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    administered_by_email = serializers.EmailField(
        source='administered_by.email', read_only=True,
    )

    class Meta:
        model = VaccinationRecord
        fields = [
            'id', 'animal_patient_id', 'vaccine_name', 'administered_on',
            'next_due_on', 'batch_number', 'administered_by_email', 'notes', 'created_at',
        ]
        read_only_fields = ['created_at']

    def validate_administered_on(self, value):
        from django.utils.timezone import now
        if value > now().date():
            raise serializers.ValidationError('Administered date cannot be in the future.')
        return value


# ---------------------------------------------------------------------------
# Weight record
# ---------------------------------------------------------------------------

class WeightRecordSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )

    class Meta:
        model = WeightRecord
        fields = [
            'id', 'animal_patient_id', 'measured_on', 'weight_kg', 'bcs',
            'notes', 'created_at',
        ]
        read_only_fields = ['created_at']

    def validate_weight_kg(self, value):
        if value <= 0 or value >= 2000:
            raise serializers.ValidationError('Weight must be between 0 and 2000 kg.')
        return value

    def validate_bcs(self, value):
        if value is not None and not (1 <= value <= 9):
            raise serializers.ValidationError('BCS must be between 1 and 9.')
        return value


# ---------------------------------------------------------------------------
# Appointment
# ---------------------------------------------------------------------------

class AppointmentSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    animal_name  = serializers.CharField(source='animal_patient.name', read_only=True)
    owner_name   = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'animal_patient_id', 'animal_name', 'owner_name',
            'attending_vet', 'appointment_type', 'scheduled_at',
            'duration_minutes', 'status', 'notes', 'linked_visit',
            'reminder_sent', 'created_at',
        ]
        read_only_fields = ['reminder_sent', 'created_at', 'linked_visit']

    @extend_schema_field(OpenApiTypes.STR)
    def get_owner_name(self, obj):
        return str(obj.animal_patient.owner)


# ---------------------------------------------------------------------------
# Prescription
# ---------------------------------------------------------------------------

from .models import Prescription, AllergyRecord, ClinicalPhoto, LabResult


class PrescriptionSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    prescribed_by_email = serializers.EmailField(
        source='prescribed_by.email', read_only=True,
    )

    class Meta:
        model = Prescription
        fields = [
            'id', 'animal_patient_id', 'visit', 'prescribed_on',
            'medication_name', 'dose', 'route', 'frequency',
            'duration_days', 'refills_remaining', 'notes',
            'prescribed_by_email', 'created_at',
        ]
        read_only_fields = ['created_at']

    def validate_prescribed_on(self, value):
        from django.utils.timezone import now
        if value > now().date():
            raise serializers.ValidationError('Prescribed date cannot be in the future.')
        return value


# ---------------------------------------------------------------------------
# Allergy record
# ---------------------------------------------------------------------------

class AllergyRecordSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    is_high_severity = serializers.BooleanField(read_only=True)

    class Meta:
        model = AllergyRecord
        fields = [
            'id', 'animal_patient_id', 'allergen', 'allergen_type',
            'reaction', 'severity', 'first_observed', 'is_high_severity',
            'created_at',
        ]
        read_only_fields = ['created_at', 'is_high_severity']


# ---------------------------------------------------------------------------
# Clinical photo
# ---------------------------------------------------------------------------

class ClinicalPhotoSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ClinicalPhoto
        fields = [
            'id', 'animal_patient_id', 'visit', 'photo', 'photo_url',
            'caption', 'body_region', 'taken_on', 'created_at',
        ]
        read_only_fields = ['created_at', 'photo_url']
        extra_kwargs = {'photo': {'write_only': True}}

    @extend_schema_field(OpenApiTypes.STR)
    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None


# ---------------------------------------------------------------------------
# Lab result
# ---------------------------------------------------------------------------

class LabResultSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = LabResult
        fields = [
            'id', 'animal_patient_id', 'visit', 'result_type', 'panel_name',
            'result_date', 'result_data', 'lab_name', 'pdf_file', 'pdf_url',
            'created_at',
        ]
        read_only_fields = ['created_at', 'pdf_url']
        extra_kwargs = {'pdf_file': {'write_only': True}}

    @extend_schema_field(OpenApiTypes.STR)
    def get_pdf_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return None


# ---------------------------------------------------------------------------
# Reproductive event
# ---------------------------------------------------------------------------

from .models import ReproductiveEvent


class ReproductiveEventSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )

    class Meta:
        model = ReproductiveEvent
        fields = [
            'id', 'animal_patient_id', 'event_type', 'event_date',
            'partner_id', 'litter_count', 'notes', 'created_at',
        ]
        read_only_fields = ['created_at']

    def validate_event_date(self, value):
        from django.utils.timezone import now
        if value > now().date():
            raise serializers.ValidationError('Event date cannot be in the future.')
        return value


# ---------------------------------------------------------------------------
# Referral network
# ---------------------------------------------------------------------------

class ReferringClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferringClinic
        fields = [
            'id', 'name', 'contact_name', 'contact_email', 'contact_phone',
            'address', 'notes', 'created_at',
        ]
        read_only_fields = ['created_at']


class ReferralPackageSerializer(serializers.ModelSerializer):
    """Clinic-facing create/manage serializer for a referral package."""
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    # Frontend holds the DICOMweb study UID, not the numeric PK (mirrors StudyShareLink).
    study_uid = serializers.CharField(write_only=True, required=False, allow_blank=True)
    animal_name = serializers.CharField(source='animal_patient.name', read_only=True)
    referring_clinic_name = serializers.CharField(source='referring_clinic.name', read_only=True)
    study_instance_uid = serializers.CharField(source='study.study_instance_uid', read_only=True)
    report_title = serializers.CharField(source='report.title', read_only=True)
    share_path = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = ReferralPackage
        fields = [
            'id', 'animal_patient_id', 'animal_name', 'referring_clinic',
            'referring_clinic_name', 'study_uid', 'study_instance_uid', 'report',
            'report_title', 'reason', 'history_summary', 'urgency',
            'token', 'recipient_email', 'expires_at', 'access_count',
            'share_path', 'is_valid', 'created_at',
        ]
        read_only_fields = ['token', 'access_count', 'created_at']

    @extend_schema_field(OpenApiTypes.STR)
    def get_share_path(self, obj):
        return f'/referral/{obj.token}'

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_valid(self, obj):
        return obj.is_valid()

    def validate_study_uid(self, value):
        if not value:
            return None
        from dicom_images.models import MedicalStudy
        try:
            return MedicalStudy.objects.get(study_instance_uid=value)
        except MedicalStudy.DoesNotExist:
            raise serializers.ValidationError('Study not found.')

    def create(self, validated_data):
        study = validated_data.pop('study_uid', None)
        if study is not None:
            validated_data['study'] = study
        return super().create(validated_data)

    def update(self, instance, validated_data):
        study = validated_data.pop('study_uid', None)
        if study is not None:
            validated_data['study'] = study
        return super().update(instance, validated_data)


class PublicReferralPackageSerializer(serializers.ModelSerializer):
    """
    Unauthenticated, sanitised view of a referral package for the receiving
    specialist. Exposes signalment, the referral reason/history, the study UID
    needed to open the viewer, and the report findings — never internal IDs.
    """
    patient = serializers.SerializerMethodField()
    referring_clinic_name = serializers.CharField(source='referring_clinic.name', read_only=True, default=None)
    study_instance_uid = serializers.CharField(source='study.study_instance_uid', read_only=True, default=None)
    report = serializers.SerializerMethodField()
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = ReferralPackage
        fields = [
            'patient', 'referring_clinic_name', 'reason', 'history_summary',
            'urgency', 'study_instance_uid', 'report', 'disclaimer', 'created_at',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_patient(self, obj):
        a = obj.animal_patient
        return {
            'name': a.name,
            'species': a.get_species_display(),
            'breed': a.breed,
            'sex': a.get_sex_display() if a.sex else '',
            'date_of_birth': a.date_of_birth.isoformat() if a.date_of_birth else None,
            'microchip_id': a.microchip_id or '',
        }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_report(self, obj):
        if not obj.report:
            return None
        content = obj.report.content or {}
        sections = content.get('sections', [])
        findings = []
        for s in sections:
            if s.get('type') == 'findings':
                for item in s.get('items', []):
                    desc = item.get('description') if isinstance(item, dict) else str(item)
                    if desc:
                        findings.append(desc)
        return {
            'title': obj.report.title,
            'findings': findings,
            'summary': content.get('summary', ''),
        }

    @extend_schema_field(OpenApiTypes.STR)
    def get_disclaimer(self, obj):
        return (
            'Shared by the referring clinic for specialist review. This is a '
            'decision-support summary, not a diagnosis, and was assisted by software.'
        )


# ---------------------------------------------------------------------------
# Owner ↔ clinic messaging
# ---------------------------------------------------------------------------

class MessageSerializer(serializers.ModelSerializer):
    animal_patient_id = serializers.PrimaryKeyRelatedField(
        queryset=AnimalPatient.objects.all(), source='animal_patient', write_only=True,
    )
    sender_email = serializers.EmailField(source='sender.email', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'animal_patient_id', 'sender_email', 'from_owner',
            'body', 'is_read', 'created_at',
        ]
        read_only_fields = ['sender_email', 'from_owner', 'is_read', 'created_at']

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Message body cannot be empty.')
        return value
