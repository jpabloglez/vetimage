# VetImage — Pending Features for Veterinary Use Cases

**Date:** 2026-06-07 (status updated 2026-06-14)  
**Status:** Historical planning reference. **All three phases (29 features) are now implemented**, and the AI analysis pipeline runs end-to-end against an in-repo reference model service, including a Cornerstone bounding-box overlay of AI findings — see [AI-WORKFLOW.md](AI-WORKFLOW.md). Remaining follow-ups: real (non-fixture) model weights, and a production-deployment hardening pass. This document is retained for the original rationale and acceptance notes per feature.  
**Audience:** Engineering, product, and clinical stakeholders

---

## Context: What the Platform Already Has

Before listing gaps, the features already in production or committed:

| Area | Current state |
|---|---|
| DICOM storage & viewer | OHIF/Cornerstone.js, DICOMweb QIDO-RS / WADO-RS |
| AI analysis framework | Connector pattern, Celery dispatch, gRPC orchestrator, WebSocket progress |
| AI models (current) | MIRAGE, CheXNet, PICAI, NNUNet, FastSurfer, STUNet — **all human-focused** |
| Patient registry | Owner → AnimalPatient → VHSMeasurement; species/breed/sex/weight (single value) |
| VHS measurement | Long + short axis in vertebral units, human-in-the-loop, trend chart |
| Study ↔ patient link | `MedicalStudy.animal_patient` FK, UI linking flow |
| Reports | PDF export, approval workflow, owner-facing public share link |
| Report templates | Generic model with `layout` JSONField; types: radiology / pathology / general / custom |
| Audit log | Auth event trail, org-scoped, filterable |
| Auth | JWT + API keys, org scoping, GDPR anonymization |

---

## Priority Key

| Symbol | Meaning |
|---|---|
| **P1** | High impact, foundational — blocks or greatly limits clinical usefulness |
| **P2** | Significant workflow improvement — clear ROI for a typical veterinary practice |
| **P3** | Differentiator or specialist feature — adds value for specific use cases |

---

## 1. Veterinary-Specific AI Models

**Why this matters first:** The current AI models (CheXNet, MIRAGE, PICAI, FastSurfer) are trained on human data and produce incorrect or meaningless results for veterinary radiographs. Species anatomy differs fundamentally — a canine thorax X-ray fed to CheXNet will produce garbage outputs. The AI analysis framework is already excellent; it needs vet-trained models plugged in.

### 1.1 Automated VHS Measurement (P1)

Currently VHS requires manual caliper placement by the clinician. Automated landmark detection would propose a measurement that the vet then confirms or corrects — the human-in-the-loop model the codebase already enforces.

**What to build:**
- New `VHSAutoConnector` following the existing `BaseAIConnector` interface
- Model input: lateral thoracic radiograph (DICOM); output: landmark coordinates (T4 cranial edge, cardiac long/short axes) + VHS value
- Frontend: render proposed landmarks on the Cornerstone.js viewer as editable overlays; vet adjusts and confirms before persisting to `VHSMeasurement` with `method='ai_assisted'`
- Seed entry: `seed_vet_models.py` (the file already exists untracked at `app/backend/ai_analysis/management/commands/seed_vet_models.py`)

**Integration points:** `VHSMeasurement.method` already has `'ai_assisted'` choice; `AIModel.supported_species` already scopes to canine/feline; `landmark_points` JSONField is already on `VHSMeasurement`.

---

### 1.2 Canine / Feline Thoracic Disease Detection (P1)

Analogous to CheXNet but trained on veterinary data. Detects: cardiomegaly, pleural effusion, pneumonia, pulmonary edema, pneumothorax, mediastinal masses.

**What to build:**
- `VetThoraxConnector` (REST + webhook, same as MIRAGE pattern)
- Output: list of findings with confidence scores, affected lung regions as bounding boxes
- Report template: "Thoracic Radiograph — Canine" and "Thoracic Radiograph — Feline" (see §5)
- `AIModel.supported_species = ["canine", "feline"]`

---

### 1.3 Hip Dysplasia Scoring — OFA / BVA / FCI (P2)

Hip radiograph evaluation is one of the highest-volume AI opportunities in small-animal practice. Output: hip joint score (OFA: Excellent/Good/Fair/Borderline/Mild/Moderate/Severe), subluxation index, femoral head congruence.

**What to build:**
- `HipDysplasiaConnector`
- New `OrthopedicFinding` model (or extend `VHSMeasurement` pattern) to persist scored results
- Supported species: canine, equine; scoring scheme selectable per study
- Report template: "Orthopedic Hip Assessment"

---

### 1.4 Dental Radiograph Analysis (P2)

Dental radiographs (intraoral X-rays) are routine in companion animal practice and largely unassisted today.

**What to build:**
- `VetDentalConnector`
- Detects: tooth resorption, periapical lesion, crown fracture, retained roots, bone loss
- Per-tooth annotation overlay on DICOM viewer
- `AIModel.supported_species = ["canine", "feline"]`

---

### 1.5 Abdominal Ultrasound Organ Assessment (P3)

Automated organ size measurement and lesion flagging on abdominal ultrasound (hepatomegaly, splenomegaly, adrenal nodules, bladder wall thickening, intestinal wall layers).

**What to build:**
- `VetAbdominalUSConnector` (accepts DICOM ultrasound series)
- Output: organ measurements compared to species/weight reference ranges, flagged findings
- Reference ranges stored per species/weight band in `AIModel.parameters`

---

### 1.6 Model Seeding for Veterinary Models (P1 — infrastructure)

`seed_vet_models.py` exists but is empty. Populate it with the above models in `is_active=False` / placeholder state so the UI's model selector, filtering, and recommendation engine already works while connectors are under development.

---

## 2. Patient History & Clinical Records

**Why this matters:** The `AnimalPatient` model currently stores only static signalment (species, breed, sex, DOB, weight as a single value). A real veterinary EMR needs longitudinal records. Visits, medications, vaccinations, lab results, and clinical notes are the backbone of patient care.

### 2.1 Visit / Consultation Records (P1)

The single most important missing model. Every clinical encounter should produce a structured record.

**Backend — new model `ClinicalVisit`:**
```
ClinicalVisit
  animal_patient → FK AnimalPatient
  visit_date: DateTimeField
  visit_type: CharField  # consultation / follow_up / vaccination / surgery / imaging / emergency
  attending_vet: FK User
  chief_complaint: TextField
  # SOAP structure
  subjective: TextField     # owner's description
  objective: TextField      # clinical exam findings
  assessment: TextField     # diagnosis / differential diagnosis
  plan: TextField           # treatment plan, next steps
  weight_kg: DecimalField   # weight at this visit (not AnimalPatient.weight_kg)
  temperature_celsius: DecimalField
  heart_rate_bpm: IntegerField
  respiratory_rate: IntegerField
  linked_study: FK MedicalStudy (nullable)
  linked_report: FK Report (nullable)
```

**Frontend:** Visit timeline on `PatientsPage` patient detail modal, collapsible SOAP note per visit. "New visit" button opens a form that creates the record and optionally starts a DICOM study upload.

**Note:** `AnimalPatient.weight_kg` should remain for the "current/registration weight" but is superseded by the per-visit value for trend purposes.

---

### 2.2 Weight & Vital Signs History (P1)

Currently `AnimalPatient.weight_kg` is a single overwritten value. The existing `VHSMeasurement` pattern (time series, chart, human-in-the-loop) should be replicated for weight.

**Option A (minimal):** Weight is captured per `ClinicalVisit` (§2.1); the chart queries visits.  
**Option B (standalone):** A `WeightRecord` model mirroring `VHSMeasurement` structure — measured_on, weight_kg, BCS (Body Condition Score 1–9), recorded_by.

BCS is veterinary-specific (Purina scale 1–9 or WSAVA scale): it is NOT just weight; it assesses fat coverage visually. Displaying BCS alongside weight greatly improves the clinical picture.

**Frontend:** Extend the existing VHS trend chart panel in patient detail to show weight over time; add BCS badge. Reuse `recharts` `LineChart` already in place.

---

### 2.3 Vaccination Records (P1)

**Backend — new model `VaccinationRecord`:**
```
VaccinationRecord
  animal_patient → FK AnimalPatient
  vaccine_name: CharField       # e.g. "Rabies", "DHPPiL", "Bordetella"
  administered_on: DateField
  next_due_on: DateField (nullable)
  batch_number: CharField
  administered_by: FK User
  notes: TextField
```

**Frontend:** "Vaccinations" tab in patient detail. Upcoming vaccinations sorted by `next_due_on` surface as reminders (§7).

**Export:** Vaccination certificate PDF (see §5.3).

---

### 2.4 Medication & Prescription History (P2)

**Backend — new model `Prescription`:**
```
Prescription
  animal_patient → FK AnimalPatient
  prescribed_by: FK User
  prescribed_on: DateField
  medication_name: CharField
  dose: CharField           # e.g. "5mg/kg"
  route: CharField          # oral / topical / injection / inhalation
  frequency: CharField      # BID / SID / PRN / …
  duration_days: IntegerField (nullable)
  refills_remaining: IntegerField default 0
  notes: TextField
  visit: FK ClinicalVisit (nullable)
```

No drug database integration needed initially — free-text medication name is sufficient. Drug interaction checking (§2.4b) is P3.

---

### 2.5 Allergy & Adverse Reaction Tracking (P2)

**Backend — new model `AllergyRecord`:**
```
AllergyRecord
  animal_patient → FK AnimalPatient
  allergen: CharField        # medication name, food, environmental
  allergen_type: CharField   # drug / food / environmental / contact
  reaction: TextField
  severity: CharField        # mild / moderate / severe / life_threatening
  first_observed: DateField
  recorded_by: FK User
```

Allergies surface as a prominent warning banner in any form that involves prescribing or anesthesia.

---

### 2.6 Surgical & Procedure History (P2)

**Backend — extend `ClinicalVisit` with a related `ProcedureRecord`:**
```
ProcedureRecord
  visit: FK ClinicalVisit
  procedure_name: CharField
  performed_by: FK User
  anesthesia_used: CharField (blank=True)
  complications: TextField (blank=True)
  implants_materials: TextField (blank=True)  # for orthopedic hardware
```

---

### 2.7 Reproductive Records (P3)

Relevant for breeding animals and intact pets. Track heat cycles, matings, pregnancies, litters.

**Backend — new model `ReproductiveEvent`:**
```
ReproductiveEvent
  animal_patient → FK AnimalPatient
  event_type: CharField   # heat / mating / pregnancy_confirmed / whelping / litter_registration
  event_date: DateField
  partner_id: CharField (blank=True)   # sire/dam identifier
  litter_count: IntegerField (nullable)
  notes: TextField
```

---

## 3. Pet Pictures & Media

**Why this matters:** Photos are used clinically for wound monitoring, dermatology follow-up, mass tracking, and simply for owner and staff recognition of the patient. The current platform has no non-DICOM media attached to an `AnimalPatient`.

### 3.1 Animal Profile Photo (P2)

**Backend — add `profile_photo` field to `AnimalPatient`:**
```python
profile_photo = models.ImageField(upload_to='patients/photos/', blank=True, null=True)
```

Store via Django's `MEDIA_ROOT` (already configured for user avatars). Serve via `MEDIA_URL`.

**Frontend:** Circular avatar in patient detail; upload via the existing `ImageUploader` component pattern or a simple `<input type="file">` with preview.

---

### 3.2 Clinical Photo Documentation (P2)

Photos taken during consultations documenting wounds, skin lesions, masses, post-operative sites. Not DICOM — standard JPEG/PNG with clinical metadata.

**Backend — new model `ClinicalPhoto`:**
```
ClinicalPhoto
  animal_patient → FK AnimalPatient
  visit → FK ClinicalVisit (nullable)
  photo: ImageField upload_to='patients/clinical/'
  caption: CharField
  body_region: CharField (blank=True)   # "left flank", "oral cavity", etc.
  taken_on: DateField
  taken_by: FK User
```

**Frontend:** Photo gallery in patient detail. Supports sorting by date, filtering by body region. "Before / after" pair view for wound healing documentation.

---

### 3.3 Media Privacy & GDPR (P1 — dependency for §3.1 and §3.2)

Pet photos are PII for the owner (may reveal location, home, owner's face). Apply the same anonymization mechanism as `Owner.anonymize_pii()`: add a `anonymize_media()` method to `AnimalPatient` that deletes profile_photo and nulls clinical photo FKs (or marks them anonymized).

---

## 4. Appointment Calendar

**Why this matters:** Without scheduling, the platform has no concept of time beyond the study upload date. A calendar bridges the gap between imaging data and the clinical encounter it belongs to.

### 4.1 Appointment Model (P1)

**Backend — new model `Appointment`:**
```
Appointment
  animal_patient → FK AnimalPatient
  attending_vet: FK User
  appointment_type: CharField   # imaging / consultation / surgery / vaccination / follow_up / emergency
  scheduled_at: DateTimeField
  duration_minutes: IntegerField default=30
  status: CharField             # pending / confirmed / completed / cancelled / no_show
  notes: TextField
  linked_visit: FK ClinicalVisit (nullable, set on completion)
  created_by: FK User
  reminder_sent: BooleanField default=False
```

**Organization scoping:** `AnimalPatient → Owner → organization`, so appointments are automatically org-scoped.

---

### 4.2 Calendar View (P1)

**Frontend — new `CalendarPage`:**
- Weekly / monthly grid view (use `react-big-calendar` or a lightweight custom grid)
- Color-coded by appointment type
- Click appointment → opens patient detail side panel
- "New appointment" flow: search owner → select animal → pick slot → confirm
- Vet filter: show only your appointments or all clinic appointments (role-gated)

---

### 4.3 Appointment Reminders (P2)

**Backend — Celery beat task:**
```python
# Run hourly; find appointments in 24h with reminder_sent=False
# Send email/notification to owner; set reminder_sent=True
```

Notification channel: email initially. SMS integration (Twilio) is P3.

**Owner notification content:** appointment time, clinic address, what to bring, cancellation link (signed URL).

---

### 4.4 Recurring Appointment Templates (P3)

For scheduled rechecks, chronic disease monitoring, vaccination boosters. Define a recurrence rule (e.g., "every 6 months") and auto-generate future `Appointment` records.

---

## 5. Reporting Templates — Veterinary-Specific

The `ReportTemplate` model exists with a `layout` JSONField and types `radiology / pathology / general / custom`. What's missing is any pre-built veterinary content and a species/modality-aware template selection UI.

### 5.1 Template Type Expansion (P1)

Add `template_type` choices:

```python
TEMPLATE_TYPE_CHOICES = [
    # existing
    ('radiology', 'Radiology'),
    ('pathology', 'Pathology'),
    ('general', 'General'),
    ('custom', 'Custom'),
    # new
    ('thoracic_canine', 'Thoracic Radiograph — Canine'),
    ('thoracic_feline', 'Thoracic Radiograph — Feline'),
    ('thoracic_equine', 'Thoracic Radiograph — Equine'),
    ('abdominal_us', 'Abdominal Ultrasound'),
    ('orthopedic', 'Orthopedic Assessment'),
    ('dental', 'Dental Radiograph'),
    ('cardiac_vhs', 'Cardiac / VHS Report'),
    ('discharge_summary', 'Discharge Summary'),
    ('vaccination_certificate', 'Vaccination Certificate'),
    ('referral_letter', 'Specialist Referral'),
    ('soap_note', 'SOAP Clinical Note'),
]
```

---

### 5.2 Species & Modality Template Filtering (P1)

**Backend — add fields to `ReportTemplate`:**
```python
species_filter = models.JSONField(default=list, blank=True)   # [] means "all species"
modality_filter = models.JSONField(default=list, blank=True)  # DICOM modality codes: CR, DX, US, CT…
```

**Frontend:** On the "new report" form, filter the template dropdown by the study's modality and the patient's species. This narrows a list of 20+ templates to the 2–3 actually relevant ones.

---

### 5.3 Vaccination Certificate Template (P2)

A specific PDF template required by many countries for pet travel. Content: owner details, animal signalment, microchip number, vaccine name + date + batch + next-due, administering vet signature field.

**Output:** PDF via existing ReportLab pipeline. The `pdf_generator.py` service already handles template-driven PDF generation.

---

### 5.4 Discharge Summary Template (P2)

Post-surgery or post-hospitalization summary for the owner: what happened, medications to give at home, wound care instructions, activity restrictions, follow-up date.

---

### 5.5 Referral Letter Template (P2)

Structured letter for specialist referral: referring vet details, reason for referral, relevant history summary, list of attached studies (DICOM UIDs), urgency. Auto-populates from the patient record and linked studies.

---

## 6. Image & Report Sharing

The platform currently supports report sharing (owner-facing read-only token link). What's missing is vet-to-vet and clinic-to-specialist sharing.

### 6.1 DICOM Study Sharing Between Clinics (P2)

**Backend — new model `StudyShareLink`:**
```
StudyShareLink
  study → FK MedicalStudy
  created_by → FK User
  recipient_email: EmailField (blank=True)   # for audit
  token: UUIDField unique
  expires_at: DateTimeField (nullable)
  access_count: IntegerField default=0
  max_accesses: IntegerField nullable
```

Endpoint: `GET /api/dicom/shared/<uuid:token>/wado/` — proxies WADO-RS for the linked study. No auth required but token-gated.

**Frontend:** "Share study" button in study browser → generates link → copy to clipboard or email via `mailto:`. Expiry configurable (7 days / 30 days / never).

---

### 6.2 Referral Package (Images + Report + History Summary) (P2)

Bundle a study, its associated report, and a condensed patient history into a single portable link or downloadable ZIP for specialist referral.

**Backend:** A `ReferralPackage` model that references a `StudyShareLink` + a `Report` + a snapshot of the patient's signalment and recent visit notes. Rendered as a landing page (similar to `OwnerReportPage`) visible to the receiving specialist without login.

---

### 6.3 Annotation Sharing (P3)

Export/share DICOM SR (Structured Report) annotations or OHIF-format annotation JSON alongside the study link, so the receiving vet sees the referring vet's markings.

---

### 6.4 DICOM CD / USB Export (P3)

Generate a standards-compliant DICOM CD structure (DICOMDIR + studies) for physical media delivery when digital sharing is not possible (rural clinics, owner requests physical copy).

---

## 7. Notifications & Reminder System

### 7.1 Notification Infrastructure (P1 — dependency for §4.3, §7.2, §7.3)

The `credentials` app already tracks sessions and events. What's missing is a proactive notification model.

**Backend — new model `Notification`** (may already exist in `credentials` app — verify):
```
Notification
  recipient → FK User
  notification_type: CharField   # vaccination_due / appointment_reminder / result_ready / …
  title: CharField
  body: TextField
  animal_patient → FK AnimalPatient (nullable)
  is_read: BooleanField default=False
  created_at: DateTimeField auto_now_add
```

WebSocket consumer for `notifications` channel (extend existing `ai_analysis` WebSocket infrastructure). Frontend: notification bell in Navbar with unread count badge.

---

### 7.2 Vaccination Due Reminders (P2)

Celery beat task (daily): query `VaccinationRecord` where `next_due_on` is in 14 / 7 / 1 days and no reminder has been sent for that window. Create a `Notification` for the attending vet and optionally email the owner.

---

### 7.3 Abnormal Finding Alerts (P2)

When an AI analysis task completes and the result contains a finding above a configurable confidence threshold (e.g., VHS > reference range, AI flags "pleural effusion"), create a `Notification` for the ordering vet with a direct link to the study.

---

## 8. Owner Portal Enhancements

Currently the owner only sees a single shared report at `/shared/:token`. A proper owner portal would increase engagement and reduce phone calls to the clinic.

### 8.1 Owner Account (P3)

Allow owners to create a login tied to their `Owner` record (linked via email). Authenticated owners see all their pets' shared reports, upcoming appointments, and vaccination reminders.

**Security:** Owner accounts have a separate role from clinic staff. They can only see their own animals. No access to DICOM studies unless an explicit `StudyShareLink` has been issued.

---

### 8.2 Pet Passport / Travel Health Certificate (P3)

Downloadable PDF summarizing: animal signalment, microchip number, owner contact, vaccination history, recent health checks. Required for EU pet travel (EU Pet Passport format) and airline travel.

---

### 8.3 Owner Messaging (P3)

Secure in-app messaging thread between owner and clinic. Replaces unstructured WhatsApp/email communication about results. All messages stored against the `AnimalPatient` record for audit.

---

## 9. Laboratory Results Integration

Lab results are currently completely outside the system. Vets manually annotate results in free-text notes.

### 9.1 Lab Result Model (P2)

**Backend — new model `LabResult`:**
```
LabResult
  animal_patient → FK AnimalPatient
  visit → FK ClinicalVisit (nullable)
  result_type: CharField   # hematology / biochemistry / urinalysis / cytology / serology / microbiology
  panel_name: CharField    # e.g. "CBC with differential", "Basic metabolic panel"
  result_date: DateField
  result_data: JSONField   # flexible key:value pairs (analyte: {value, unit, reference_low, reference_high, flag})
  lab_name: CharField
  requested_by → FK User
  pdf_file: FileField (nullable)   # original lab PDF if available
```

**Frontend:** Lab results tab in patient detail. Color-coded flags (H/L/CRITICAL) for out-of-range values. Trend chart for serial analytes (e.g., creatinine trend for CKD monitoring).

---

### 9.2 HL7 / FHIR Lab Import (P3)

Structured import of lab results from external analyzers using HL7 v2 ORU messages or FHIR `DiagnosticReport` resources. Many in-house analyzers (IDEXX, Heska, Abaxis) can export HL7 messages.

---

## 10. Extended Animal Details

### 10.1 Microchip Registry Integration (P2)

The `AnimalPatient.microchip_id` field exists but is isolated. Connect it to public/national microchip registries (PetMaxx, EUROPETNET, AKC Reunite) via API for:
- Ownership verification
- Lost/found reporting
- Population-level statistics

---

### 10.2 Breed-Specific Reference Ranges (P2)

VHS reference ranges are already species-specific (canine 8.5–10.6, feline 6.7–8.1). This pattern should be extended to:
- Weight (breed-specific typical range for BCS context)
- Lab analytes (greyhounds have lower PCV reference ranges than other breeds)
- Hip scores (OFA breed-specific pass rates)

**Implementation:** A `BreedReference` model or a `breed_references` JSONField on `AIModel` seeded from published breed-specific datasets.

---

### 10.3 Insurance Information (P3)

```python
# Add to AnimalPatient
insurance_provider = models.CharField(max_length=100, blank=True)
insurance_policy_number = models.CharField(max_length=100, blank=True)
insurance_expiry = models.DateField(null=True, blank=True)
```

Displayed in the patient header as a reminder to check coverage before procedures. Insurance claim PDF generation (P3) is a downstream feature.

---

## 11. Multi-Clinic & Referral Network

### 11.1 Referring Clinic Model (P2)

**Backend — new model `ReferringClinic`:**
```
ReferringClinic
  organization → FK Organization (the receiving specialist clinic)
  name: CharField
  address: CharField
  contact_email: EmailField
  contact_phone: CharField
  notes: TextField
```

Allows tagging a `ClinicalVisit` or `MedicalStudy` as "referred from" for proper attribution and result communication.

---

### 11.2 Case Transfer (P3)

Transfer an `AnimalPatient`'s full record (visits, studies, reports, VHS measurements) to another clinic's organization within the platform. Requires careful org-scoping review and owner consent tracking.

---

## 12. Implementation Priority Summary

### Phase 1 — Clinical Foundation (P1 items, highest ROI)

These unblock meaningful clinical use:

1. `ClinicalVisit` model with SOAP notes and vital signs at each visit
2. `WeightRecord` time series (or weight-per-visit from `ClinicalVisit`)
3. `VaccinationRecord` model
4. Calendar: `Appointment` model + weekly/monthly UI view
5. Species/modality-aware report template filtering
6. `seed_vet_models.py`: populate with vet-specific AI model stubs (VHSAuto, VetThorax)
7. Notification infrastructure (model + WebSocket channel)
8. Animal profile photo (`profile_photo` field on `AnimalPatient`)

### Phase 2 — Workflow Completeness (P2 items)

9. Vaccination due reminders (Celery beat)
10. `Prescription` / medication history
11. `AllergyRecord` with warning banner in prescribing forms
12. Clinical photo documentation (`ClinicalPhoto`)
13. Automated VHS measurement connector (vet-trained landmark model)
14. Canine/feline thoracic disease AI connector
15. Veterinary-specific report templates (thoracic, cardiac, discharge, referral)
16. `LabResult` model and UI
17. Study share link (`StudyShareLink`) for vet-to-vet sharing
18. Referral package (study + report + history bundle)

### Phase 3 — Differentiation (P3 items)

19. Hip dysplasia scoring AI connector
20. Dental radiograph AI connector
21. Owner account and owner portal
22. Owner messaging
23. HL7/FHIR lab import
24. Referral network (multi-clinic)
25. Pet passport / travel health certificate
26. Reproductive records
27. DICOM CD/USB export
28. Breed-specific reference ranges
29. Insurance information and claim support

---

## 13. Data Model Dependency Graph

```
Organization
  └── Owner (email + phone required)
        └── AnimalPatient
              ├── profile_photo [NEW §3.1]
              ├── ClinicalPhoto[] [NEW §3.2]
              ├── ClinicalVisit[] [NEW §2.1]
              │     ├── weight_kg (per-visit vital)
              │     ├── ProcedureRecord [NEW §2.6]
              │     └── linked_study → MedicalStudy
              ├── VaccinationRecord[] [NEW §2.3]
              ├── Prescription[] [NEW §2.4]
              ├── AllergyRecord[] [NEW §2.5]
              ├── LabResult[] [NEW §9.1]
              ├── WeightRecord[] [NEW §2.2, alt to per-visit]
              ├── VHSMeasurement[] [EXISTS]
              ├── Appointment[] [NEW §4.1]
              │     └── linked_visit → ClinicalVisit
              └── ReproductiveEvent[] [NEW §2.7]

MedicalStudy (DICOM)
  ├── animal_patient → AnimalPatient [EXISTS]
  ├── StudyShareLink [NEW §6.1]
  └── Report
        ├── approved_by, share_token [EXISTS]
        └── ReferralPackage [NEW §6.2]

AIModel
  ├── supported_species [EXISTS]
  ├── VHSAutoConnector [NEW §1.1]
  ├── VetThoraxConnector [NEW §1.2]
  ├── HipDysplasiaConnector [NEW §1.3]
  └── VetDentalConnector [NEW §1.4]

ReportTemplate
  ├── species_filter [NEW §5.2]
  ├── modality_filter [NEW §5.2]
  └── new template_type choices [NEW §5.1]
```

---

## 14. Technical Notes for Implementers

**Reuse existing patterns:**
- Time series + trend chart → copy `VHSMeasurement` model + `VHSPanel` React component pattern for weight, lab analytes, any other serial measurement.
- Organization scoping → every new model must reach `organization` within 2 FK hops; use `get_or_create_organization()` in views.
- Celery tasks → use `monitoring` queue for reminders/alerts, `default` for everything else.
- Public unauthenticated views → follow `PublicSharedReportView` pattern: token lookup, `IsAuthenticated` off, explicit response throttling.
- PDF generation → extend `pdf_generator.py` service; new templates add entries to `template_engine.py`.
- AI connectors → implement `BaseAIConnector`, register in `seed_vet_models.py`, set `supported_species`.
- Frontend validation → add schemas to `utils/validation.ts`; use `zodFieldErrors()` for inline error display.
- i18n → add keys to all three locale files (`en/es/pt`) before raising a PR; the `patients` namespace is the right home for clinical record strings.
- `getByLabelText` in tests → use anchored regex (`/^Field name/i`) to avoid matching the search bar's `aria-label`.

**New Celery queues to consider:**
- `reminders` — appointment and vaccination reminder emails (low priority, high volume, tolerates delay)
- `notifications` — real-time in-app notification creation (should be fast but non-critical)

**GDPR / PII:**
- Every new model that stores owner-identifiable information (photos, visit notes with personal details) must implement an `anonymize()` method or be cascaded from `Owner.anonymize_pii()`.
- Clinical photos are PII. Apply `AnimalPatient.anonymize_media()` (§3.3) before any data retention expiry.

---

*Document owner: Engineering lead. Update this file as features are scoped and implemented. Cross-reference with `docs/VETERINARY_ALIGNMENT_REPORT.md` for clinical justification of each feature.*
