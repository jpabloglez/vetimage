import uuid

from django.db import models


SPECIES_CHOICES = [
    ('canine', 'Canine'),
    ('feline', 'Feline'),
    ('equine', 'Equine'),
    ('bovine', 'Bovine'),
    ('avian', 'Avian'),
    ('exotic', 'Exotic'),
    ('other', 'Other'),
]

SEX_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('MN', 'Male Neutered'),
    ('FS', 'Female Spayed'),
    ('U', 'Unknown'),
]

VISIT_TYPE_CHOICES = [
    ('consultation', 'Consultation'),
    ('follow_up', 'Follow-up'),
    ('vaccination', 'Vaccination'),
    ('surgery', 'Surgery'),
    ('imaging', 'Imaging'),
    ('emergency', 'Emergency'),
]

APPOINTMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('no_show', 'No Show'),
]

BCS_CHOICES = [(i, str(i)) for i in range(1, 10)]  # 1–9 Purina/WSAVA scale


class Owner(models.Model):
    """
    Animal owner / guardian. Owner PII is GDPR-scoped to the clinic organization.
    """
    organization = models.ForeignKey(
        'users.Organization',
        on_delete=models.CASCADE,
        related_name='owners',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    # GDPR data-retention: scrubbed owners keep their record (so study links
    # survive) but their personal data is removed once the retention window passes.
    pii_anonymized = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Owner'
        verbose_name_plural = 'Owners'
        indexes = [
            models.Index(fields=['organization', 'last_name']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def anonymize_pii(self):
        """Remove personally-identifying data while keeping the record/links."""
        self.first_name = '[redacted]'
        self.last_name = '[redacted]'
        self.email = ''
        self.phone = ''
        self.address = ''
        self.city = ''
        self.country = ''
        self.pii_anonymized = True
        self.save(update_fields=[
            'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'country', 'pii_anonymized', 'updated_at',
        ])


class AnimalPatient(models.Model):
    """
    Veterinary patient. One owner may have many animal patients.
    """
    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name='animals',
    )
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES, db_index=True)
    breed = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=2, choices=SEX_CHOICES, blank=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    microchip_id = models.CharField(max_length=50, blank=True, db_index=True)
    color = models.CharField(max_length=100, blank=True)
    profile_photo = models.ImageField(
        upload_to='patients/photos/', blank=True, null=True,
    )
    # Pet insurance — surfaced as a reminder to check coverage before procedures.
    insurance_provider     = models.CharField(max_length=100, blank=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    insurance_expiry       = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Animal Patient'
        verbose_name_plural = 'Animal Patients'
        indexes = [
            models.Index(fields=['owner', 'species']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_species_display()}) — {self.owner}"

    def anonymize_media(self):
        """Delete profile photo for GDPR retention expiry."""
        if self.profile_photo:
            self.profile_photo.delete(save=False)
            self.profile_photo = None
            self.save(update_fields=['profile_photo'])


# Vertebral Heart Score reference ranges (vertebral units). Breed-dependent;
# these are widely-cited population guides used only to label a measurement as
# within/above the typical range — never as a diagnosis.
VHS_REFERENCE = {
    'canine': {'low': 8.5, 'high': 10.6},
    'feline': {'low': 6.7, 'high': 8.1},
}


class VHSMeasurement(models.Model):
    """
    A Vertebral Heart Score measurement for an animal patient.

    VHS is a *measurement* (defensible decision-support), not a diagnosis. The
    long and short cardiac axes are each expressed in vertebral-body units
    (counted from the cranial edge of T4); VHS = long + short. Landmark points
    may be proposed by an assist model but are always veterinarian-editable, and
    the clinician confirms the final value (human-in-the-loop).
    """
    METHOD_CHOICES = [
        ('manual', 'Manual'),
        ('ai_assisted', 'AI-assisted (clinician-confirmed)'),
    ]

    animal_patient = models.ForeignKey(
        AnimalPatient,
        on_delete=models.CASCADE,
        related_name='vhs_measurements',
    )
    # Optional link to the source study/image (DICOM natural keys).
    study_instance_uid = models.CharField(max_length=200, blank=True, db_index=True)
    sop_instance_uid = models.CharField(max_length=200, blank=True)

    measured_on = models.DateField(
        help_text="Date of the radiograph the measurement was taken from",
    )
    long_axis_vertebrae = models.DecimalField(
        max_digits=4, decimal_places=1,
        help_text="Long cardiac axis in vertebral units (e.g. 5.5)",
    )
    short_axis_vertebrae = models.DecimalField(
        max_digits=4, decimal_places=1,
        help_text="Short cardiac axis in vertebral units (e.g. 4.5)",
    )
    vhs = models.DecimalField(
        max_digits=4, decimal_places=1,
        help_text="Computed VHS = long + short (vertebral units)",
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='manual')
    # Caliper/landmark coordinates so a measurement can be re-opened and edited.
    landmark_points = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vhs_measurements',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-measured_on', '-created_at']
        verbose_name = 'VHS Measurement'
        verbose_name_plural = 'VHS Measurements'
        indexes = [
            models.Index(fields=['animal_patient', '-measured_on']),
        ]

    def save(self, *args, **kwargs):
        # VHS is always the sum of the two axes — compute server-side so it can
        # never drift from its components.
        self.vhs = (self.long_axis_vertebrae or 0) + (self.short_axis_vertebrae or 0)
        super().save(*args, **kwargs)

    def _reference_range(self):
        """
        Resolve the VHS reference range for this animal: a breed-specific
        BreedReference row takes precedence over the species-wide population
        default in VHS_REFERENCE.
        """
        animal = self.animal_patient
        ref = BreedReference.lookup(animal.species, animal.breed, 'vhs')
        if ref:
            return ref
        return VHS_REFERENCE.get(animal.species)

    @property
    def interpretation(self):
        """within_range / above_range / below_range / unknown (breed/species-dependent)."""
        ref = self._reference_range()
        if not ref or self.vhs is None:
            return 'unknown'
        v = float(self.vhs)
        if v > ref['high']:
            return 'above_range'
        if v < ref['low']:
            return 'below_range'
        return 'within_range'

    def __str__(self):
        return f"VHS {self.vhs} ({self.animal_patient.name}, {self.measured_on})"


class ClinicalVisit(models.Model):
    """
    A clinical encounter (SOAP note + vitals) for an animal patient.
    """
    animal_patient = models.ForeignKey(
        AnimalPatient,
        on_delete=models.CASCADE,
        related_name='visits',
    )
    visit_date = models.DateTimeField()
    visit_type = models.CharField(
        max_length=20, choices=VISIT_TYPE_CHOICES,
        default='consultation', db_index=True,
    )
    attending_vet = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='vet_visits',
    )
    chief_complaint = models.TextField(blank=True)
    # SOAP
    subjective  = models.TextField(blank=True)
    objective   = models.TextField(blank=True)
    assessment  = models.TextField(blank=True)
    plan        = models.TextField(blank=True)
    # Vitals captured at this specific visit
    weight_kg           = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    temperature_celsius = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    heart_rate_bpm      = models.PositiveIntegerField(null=True, blank=True)
    respiratory_rate    = models.PositiveIntegerField(null=True, blank=True)
    # Optional links to associated DICOM study and report
    linked_study = models.ForeignKey(
        'dicom_images.MedicalStudy',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clinical_visits',
    )
    linked_report = models.ForeignKey(
        'reports.Report',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clinical_visits',
    )
    referred_by = models.ForeignKey(
        'patients.ReferringClinic',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='visits',
        help_text="External clinic this case was referred from.",
    )
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_visits',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Clinical Visit'
        verbose_name_plural = 'Clinical Visits'
        indexes = [
            models.Index(fields=['animal_patient', '-visit_date']),
        ]

    def __str__(self):
        return f"{self.get_visit_type_display()} — {self.animal_patient.name} ({self.visit_date.date()})"


class VaccinationRecord(models.Model):
    """
    Vaccination administered to an animal patient.
    """
    animal_patient = models.ForeignKey(
        AnimalPatient,
        on_delete=models.CASCADE,
        related_name='vaccinations',
    )
    vaccine_name    = models.CharField(max_length=200)
    administered_on = models.DateField()
    next_due_on     = models.DateField(null=True, blank=True, db_index=True)
    batch_number    = models.CharField(max_length=100, blank=True)
    administered_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='administered_vaccinations',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-administered_on']
        verbose_name = 'Vaccination Record'
        verbose_name_plural = 'Vaccination Records'
        indexes = [
            models.Index(fields=['animal_patient', 'next_due_on']),
        ]

    def __str__(self):
        return f"{self.vaccine_name} — {self.animal_patient.name} ({self.administered_on})"


class WeightRecord(models.Model):
    """
    Time-series weight measurement with optional Body Condition Score (BCS 1–9).
    Mirrors VHSMeasurement for trend-charting consistency.
    """
    animal_patient = models.ForeignKey(
        AnimalPatient,
        on_delete=models.CASCADE,
        related_name='weight_records',
    )
    measured_on = models.DateField()
    weight_kg   = models.DecimalField(max_digits=6, decimal_places=2)
    bcs         = models.PositiveSmallIntegerField(
        null=True, blank=True,
        choices=BCS_CHOICES,
        help_text="Body Condition Score 1–9 (Purina/WSAVA scale). 1=emaciated, 5=ideal, 9=obese.",
    )
    recorded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='weight_records',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-measured_on']
        verbose_name = 'Weight Record'
        verbose_name_plural = 'Weight Records'
        indexes = [
            models.Index(fields=['animal_patient', '-measured_on']),
        ]

    def __str__(self):
        return f"{self.weight_kg} kg — {self.animal_patient.name} ({self.measured_on})"


class Appointment(models.Model):
    """
    Scheduled clinic appointment for an animal patient.
    """
    animal_patient = models.ForeignKey(
        AnimalPatient,
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    attending_vet = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments',
    )
    appointment_type = models.CharField(
        max_length=20,
        choices=VISIT_TYPE_CHOICES,
        default='consultation',
    )
    scheduled_at     = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    status = models.CharField(
        max_length=20,
        choices=APPOINTMENT_STATUS_CHOICES,
        default='pending',
        db_index=True,
    )
    notes        = models.TextField(blank=True)
    linked_visit = models.OneToOneField(
        ClinicalVisit,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointment',
    )
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_appointments',
    )
    reminder_sent = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_at']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        indexes = [
            models.Index(fields=['animal_patient', 'scheduled_at']),
            models.Index(fields=['attending_vet', 'scheduled_at']),
            models.Index(fields=['status', 'scheduled_at']),
        ]

    def __str__(self):
        return (
            f"{self.get_appointment_type_display()} — "
            f"{self.animal_patient.name} ({self.scheduled_at:%Y-%m-%d %H:%M})"
        )


ROUTE_CHOICES = [
    ('oral', 'Oral'),
    ('topical', 'Topical'),
    ('injection_sc', 'Subcutaneous injection'),
    ('injection_im', 'Intramuscular injection'),
    ('injection_iv', 'Intravenous injection'),
    ('inhalation', 'Inhalation'),
    ('ophthalmic', 'Ophthalmic'),
    ('otic', 'Otic'),
    ('other', 'Other'),
]

ALLERGEN_TYPE_CHOICES = [
    ('drug', 'Drug'),
    ('food', 'Food'),
    ('environmental', 'Environmental'),
    ('contact', 'Contact'),
]

ALLERGY_SEVERITY_CHOICES = [
    ('mild', 'Mild'),
    ('moderate', 'Moderate'),
    ('severe', 'Severe'),
    ('life_threatening', 'Life-threatening'),
]

LAB_RESULT_TYPE_CHOICES = [
    ('hematology', 'Hematology'),
    ('biochemistry', 'Biochemistry'),
    ('urinalysis', 'Urinalysis'),
    ('cytology', 'Cytology'),
    ('serology', 'Serology'),
    ('microbiology', 'Microbiology'),
    ('other', 'Other'),
]


class Prescription(models.Model):
    """Medication prescribed to an animal patient at a clinical visit."""
    animal_patient = models.ForeignKey(
        AnimalPatient, on_delete=models.CASCADE, related_name='prescriptions',
    )
    prescribed_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='prescriptions',
    )
    visit = models.ForeignKey(
        ClinicalVisit, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='prescriptions',
    )
    prescribed_on   = models.DateField()
    medication_name = models.CharField(max_length=200)
    dose            = models.CharField(max_length=100, blank=True, help_text="e.g. '5 mg/kg'")
    route           = models.CharField(max_length=20, choices=ROUTE_CHOICES, blank=True)
    frequency       = models.CharField(max_length=100, blank=True, help_text="e.g. 'BID', 'SID', 'PRN'")
    duration_days   = models.PositiveIntegerField(null=True, blank=True)
    refills_remaining = models.PositiveSmallIntegerField(default=0)
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-prescribed_on', '-created_at']
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'
        indexes = [models.Index(fields=['animal_patient', '-prescribed_on'])]

    def __str__(self):
        return f"{self.medication_name} — {self.animal_patient.name} ({self.prescribed_on})"


class AllergyRecord(models.Model):
    """
    Known allergy or adverse reaction for an animal patient.
    Severe/life-threatening allergies surface as a warning banner in the UI
    wherever prescribing or anesthesia is involved.
    """
    animal_patient = models.ForeignKey(
        AnimalPatient, on_delete=models.CASCADE, related_name='allergies',
    )
    allergen      = models.CharField(max_length=200)
    allergen_type = models.CharField(max_length=20, choices=ALLERGEN_TYPE_CHOICES)
    reaction      = models.TextField(blank=True)
    severity      = models.CharField(max_length=20, choices=ALLERGY_SEVERITY_CHOICES)
    first_observed = models.DateField(null=True, blank=True)
    recorded_by   = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='allergy_records',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-severity', 'allergen']
        verbose_name = 'Allergy Record'
        verbose_name_plural = 'Allergy Records'
        indexes = [models.Index(fields=['animal_patient', 'severity'])]

    def __str__(self):
        return f"{self.allergen} ({self.get_severity_display()}) — {self.animal_patient.name}"

    @property
    def is_high_severity(self):
        return self.severity in ('severe', 'life_threatening')


class ClinicalPhoto(models.Model):
    """
    Clinical photograph attached to an animal patient or a specific visit.
    Used for wound monitoring, dermatology follow-up, mass tracking, etc.
    """
    animal_patient = models.ForeignKey(
        AnimalPatient, on_delete=models.CASCADE, related_name='clinical_photos',
    )
    visit = models.ForeignKey(
        ClinicalVisit, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='photos',
    )
    photo       = models.ImageField(upload_to='patients/clinical/%Y/%m/')
    caption     = models.CharField(max_length=255, blank=True)
    body_region = models.CharField(max_length=100, blank=True)
    taken_on    = models.DateField()
    taken_by    = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='clinical_photos',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-taken_on', '-created_at']
        verbose_name = 'Clinical Photo'
        verbose_name_plural = 'Clinical Photos'
        indexes = [models.Index(fields=['animal_patient', '-taken_on'])]

    def __str__(self):
        return f"{self.animal_patient.name} — {self.taken_on} ({self.body_region or 'unspecified'})"


class LabResult(models.Model):
    """
    Laboratory result panel for an animal patient.
    result_data stores analyte→{value, unit, ref_low, ref_high, flag} maps.
    """
    animal_patient = models.ForeignKey(
        AnimalPatient, on_delete=models.CASCADE, related_name='lab_results',
    )
    visit = models.ForeignKey(
        ClinicalVisit, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lab_results',
    )
    result_type  = models.CharField(max_length=20, choices=LAB_RESULT_TYPE_CHOICES, db_index=True)
    panel_name   = models.CharField(max_length=200)
    result_date  = models.DateField(db_index=True)
    result_data  = models.JSONField(
        default=dict,
        help_text="Analyte map: {name: {value, unit, ref_low, ref_high, flag}}",
    )
    lab_name     = models.CharField(max_length=200, blank=True)
    requested_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lab_requests',
    )
    pdf_file     = models.FileField(upload_to='patients/labs/', null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-result_date', '-created_at']
        verbose_name = 'Lab Result'
        verbose_name_plural = 'Lab Results'
        indexes = [models.Index(fields=['animal_patient', '-result_date'])]

    def __str__(self):
        return f"{self.panel_name} — {self.animal_patient.name} ({self.result_date})"


REPRODUCTIVE_EVENT_CHOICES = [
    ('heat', 'Heat / Estrus'),
    ('mating', 'Mating'),
    ('pregnancy_confirmed', 'Pregnancy Confirmed'),
    ('whelping', 'Whelping / Queening / Foaling'),
    ('litter_registration', 'Litter Registration'),
    ('spay_neuter', 'Spay / Neuter'),
    ('other', 'Other'),
]


class ReproductiveEvent(models.Model):
    """
    Reproductive history event for breeding or intact animals
    (heat cycles, matings, pregnancies, litters).
    """
    animal_patient = models.ForeignKey(
        AnimalPatient, on_delete=models.CASCADE, related_name='reproductive_events',
    )
    event_type  = models.CharField(max_length=30, choices=REPRODUCTIVE_EVENT_CHOICES)
    event_date  = models.DateField()
    partner_id  = models.CharField(max_length=100, blank=True, help_text="Sire/dam identifier (microchip or registry no.)")
    litter_count = models.PositiveSmallIntegerField(null=True, blank=True)
    notes       = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reproductive_events',
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-event_date', '-created_at']
        verbose_name = 'Reproductive Event'
        verbose_name_plural = 'Reproductive Events'
        indexes = [models.Index(fields=['animal_patient', '-event_date'])]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.animal_patient.name} ({self.event_date})"


class BreedReference(models.Model):
    """
    Breed/species-specific reference range for a clinical metric.

    Used to refine population reference ranges (which are breed-dependent) for
    measurements such as VHS. A blank `breed_pattern` applies to the whole
    species. More specific (breed-matching) rows take precedence over
    species-wide rows. Reference only — never a diagnosis.
    """
    species       = models.CharField(max_length=20, choices=SPECIES_CHOICES, db_index=True)
    breed_pattern = models.CharField(
        max_length=100, blank=True,
        help_text="Case-insensitive substring matched against the animal's breed. Blank = whole species.",
    )
    metric        = models.CharField(max_length=50, default='vhs', db_index=True)
    low           = models.DecimalField(max_digits=6, decimal_places=2)
    high          = models.DecimalField(max_digits=6, decimal_places=2)
    source        = models.CharField(max_length=255, blank=True, help_text="Citation for the reference range.")
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['species', 'metric', 'breed_pattern']
        verbose_name = 'Breed Reference Range'
        verbose_name_plural = 'Breed Reference Ranges'
        indexes = [models.Index(fields=['species', 'metric'])]
        constraints = [
            models.UniqueConstraint(
                fields=['species', 'breed_pattern', 'metric'],
                name='unique_breed_reference',
            ),
        ]

    def __str__(self):
        scope = self.breed_pattern or 'all breeds'
        return f"{self.get_species_display()} / {scope} / {self.metric}: {self.low}–{self.high}"

    @classmethod
    def lookup(cls, species, breed, metric):
        """
        Return {'low', 'high', 'source'} for the most specific matching row,
        or None. Breed-matching rows win over species-wide rows.
        """
        rows = cls.objects.filter(species=species, metric=metric)
        breed_l = (breed or '').lower()
        best = None
        for row in rows:
            if row.breed_pattern:
                if row.breed_pattern.lower() in breed_l:
                    # Most specific (longest matching pattern) wins.
                    if best is None or len(row.breed_pattern) > len(best.breed_pattern):
                        best = row
            elif best is None:
                best = row  # species-wide fallback
        if best is None:
            return None
        return {'low': float(best.low), 'high': float(best.high), 'source': best.source}


# ---------------------------------------------------------------------------
# Referral network (multi-clinic)
# ---------------------------------------------------------------------------

REFERRAL_URGENCY_CHOICES = [
    ('routine', 'Routine'),
    ('urgent', 'Urgent'),
    ('emergency', 'Emergency'),
]


class ReferringClinic(models.Model):
    """
    A partner/referring clinic in the receiving organisation's address book.
    Lets a ClinicalVisit or ReferralPackage be attributed to an external clinic
    for proper communication and statistics. Organisation-scoped.
    """
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='referring_clinics',
    )
    name          = models.CharField(max_length=200)
    contact_name  = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    address       = models.CharField(max_length=300, blank=True)
    notes         = models.TextField(blank=True)
    created_by    = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_referring_clinics',
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Referring Clinic'
        verbose_name_plural = 'Referring Clinics'
        indexes = [models.Index(fields=['organization', 'name'])]

    def __str__(self):
        return self.name


class ReferralPackage(models.Model):
    """
    A portable, token-gated bundle (study + report + history snapshot) prepared
    for a specialist or partner clinic. Rendered as an unauthenticated landing
    page keyed on the unguessable token — same pattern as report sharing.
    """
    animal_patient   = models.ForeignKey(
        AnimalPatient, on_delete=models.CASCADE, related_name='referral_packages',
    )
    referring_clinic = models.ForeignKey(
        ReferringClinic, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='packages',
    )
    study  = models.ForeignKey(
        'dicom_images.MedicalStudy', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='referral_packages',
    )
    report = models.ForeignKey(
        'reports.Report', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='referral_packages',
    )
    reason          = models.TextField(blank=True)
    history_summary = models.TextField(blank=True, help_text="Condensed patient history snapshot at referral time.")
    urgency         = models.CharField(max_length=10, choices=REFERRAL_URGENCY_CHOICES, default='routine')
    token           = models.UUIDField(unique=True, default=uuid.uuid4, db_index=True)
    recipient_email = models.EmailField(blank=True, help_text="For audit trail only; not used for access control.")
    expires_at      = models.DateTimeField(null=True, blank=True)
    access_count    = models.PositiveIntegerField(default=0)
    created_by      = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_referral_packages',
    )
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Referral Package'
        verbose_name_plural = 'Referral Packages'
        indexes = [models.Index(fields=['animal_patient', '-created_at'])]

    def __str__(self):
        return f"Referral {str(self.token)[:8]}… — {self.animal_patient.name}"

    def is_valid(self):
        """Return True if the package can still be accessed publicly."""
        from django.utils import timezone
        if self.expires_at is not None and timezone.now() > self.expires_at:
            return False
        return True


# ---------------------------------------------------------------------------
# Owner ↔ clinic messaging (#22)
# ---------------------------------------------------------------------------

class Message(models.Model):
    """
    A secure message in the owner↔clinic thread for one animal. Threads are
    keyed on the animal so the whole conversation is preserved against the
    patient record for audit. `from_owner` records which side sent it (set from
    the sender's role at send time) so the UI can render the thread correctly
    even after the sender account is gone.
    """
    animal_patient = models.ForeignKey(
        AnimalPatient, on_delete=models.CASCADE, related_name='messages',
    )
    sender = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_messages',
    )
    from_owner = models.BooleanField(default=False)
    body       = models.TextField()
    is_read    = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        indexes = [models.Index(fields=['animal_patient', 'created_at'])]

    def __str__(self):
        who = 'owner' if self.from_owner else 'clinic'
        return f"Msg ({who}) — {self.animal_patient.name} @ {self.created_at:%Y-%m-%d %H:%M}"
