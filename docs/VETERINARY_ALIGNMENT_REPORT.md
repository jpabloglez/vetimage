# VetImage — Veterinary Clinical Alignment: Technical Report & Roadmap

**Date:** 2026-06-02
**Status:** Draft for review — guides continuous modification
**Audience:** Engineering, product, and clinical advisors

---

## 1. Purpose & Scope

VetImage was forked from a **human** medical-imaging platform (OpenMedLab). The brand,
landing copy, data model (`Owner → AnimalPatient → MedicalStudy`), color scheme, and port
mapping have been adapted. **However, the clinical substance of the product is still
human-medicine.** This report audits the current state against the realities of veterinary
imaging practice and the published evidence/regulatory landscape, then defines a prioritized
roadmap to make VetImage genuinely useful — and safe — for veterinarians and pet owners.

Sources for the external analysis are listed in §8.

---

## 2. Executive Summary

**What's good:** the underlying architecture (DICOMweb storage, OHIF/Cornerstone viewer,
pluggable AI connectors, Celery dispatch, structured reports, WebSocket monitoring) is a
sound, modality-agnostic foundation that maps well onto veterinary imaging.

**The core problem:** every clinically meaningful surface is still human. All eight seeded
AI models target human anatomy (retina, prostate, human chest, human brain, human CT). The
taxonomy is `medical_domains` + `anatomical_regions` with no **species** dimension. The new
`AnimalPatient`/`Owner` models are **not wired into the frontend at all** (zero references in
`app/frontend/src`). Compliance pages assert **HIPAA "Certified" / SOC 2 / GDPR** badges that
are false and, for HIPAA, categorically inapplicable to animal patients.

**The strategic insight from the evidence:** commercial veterinary AI today shows **high
specificity but dangerously low sensitivity** (≈0.69 overall, ≈0.44 on complex cases) and
**no commercial product meets ACVR/ECVDI standards for transparency, validation, or safety.**
The professional position is unambiguous: **AI must always be used with a qualified
veterinary professional in the loop.** There is **no FDA pathway** for veterinary diagnostic
AI, so the market is split between **defensible "workflow/measurement AI"** (hanging
protocols, vertebral heart score, image-quality scoring, worklist triage) and **legally
fraught "AI primary reads"** (autonomous narrative diagnosis).

**Therefore VetImage's wedge is:** a **transparent, human-in-the-loop, workflow- and
measurement-first** veterinary imaging platform — explicitly *not* an autonomous diagnostician
— with a clean Owner→Patient→Study workflow and an optional pet-owner results portal. This is
both the safest and the most differentiated position.

---

## 3. Current-State Audit (codebase)

### 3.1 Backend data model
| Element | State | Assessment |
|---|---|---|
| `patients.Owner`, `patients.AnimalPatient` | ✅ Created (species/breed/microchip/weight/sex) | Good shape; `SPECIES_CHOICES` covers canine/feline/equine/bovine/avian/exotic/other |
| `MedicalStudy.animal_patient` FK (nullable) | ✅ Added | Correct — keeps DICOM `patient_*` mirrors for QIDO-RS |
| `MedicalStudy.patient_*` (DICOM-derived) | ✅ Retained | Needed for DICOMweb; fine |
| Migrations for `patients` + FK | ⚠️ **Pending** | Must `makemigrations patients` + `migrate` before any of this runs |
| `users` roles | ✅ Relabeled (Veterinarian, Clinic Admin, Vet Radiologist…) | Labels only; OK |

### 3.2 AI model registry — **the biggest clinical gap**
`ai_analysis/management/commands/seed_ai_models.py` seeds **only human models**:

| Seeded model | Target | Veterinary relevance |
|---|---|---|
| MIRAGE | Human retinal OCT/SLO | ❌ None |
| PI-CAI nnU-Net | Human prostate MRI | ❌ None (no prostate-cancer screening in GP vet) |
| CheXNet | **Human** chest X-ray (14 pathologies) | ⚠️ Wrong anatomy/labels; canine/feline thorax differs |
| FastSurfer v2 | Human brain MRI parcellation | ❌ None |
| STU-Net S/B/L, MIS-FM | Human CT/MRI segmentation (TotalSegmentator-style) | ❌ None |

Taxonomy fields are **human-centric**: `medical_domains` (ophthalmology, urology, neurology),
`anatomical_regions` (no species). There is **no `species` / `supported_species` field**.

### 3.3 Frontend
| Area | State | Assessment |
|---|---|---|
| Brand / landing / i18n (en/es/pt) | ✅ Veterinary copy | Done in prior pass |
| **Owner/Patient/species in UI** | ❌ **Absent** | `animal_patient`, `species`, `breed`, `owner` have **zero** references in `src` — Phase-1 backend is invisible to users |
| Upload/Analyze flow (`AnalyzePage.tsx`, 960 lines) | ⚠️ Study-centric, no patient context | Cannot attach a study to an animal/owner from UI |
| `SecurityPage.tsx` | ❌ Claims HIPAA **Certified**, SOC 2 Type II, GDPR Ready | False + HIPAA inapplicable; **legal risk** |
| `StatisticsPage.tsx` (657 lines) | ⚠️ Human-framed metrics | Re-frame around species/modality/clinic |
| `LandingRef.tsx` (729 lines), `LandingPage` | ⚠️ `LandingRef` is stray/legacy | Remove or fold in (we already removed `Landing.tsx`) |
| Icons (`Stethoscope` in 7 files) | ⚠️ Human-coded but acceptable | Low priority |

### 3.4 Reports
`reports.Report.content` is free-form JSON and `ReportTemplate.template_type` exists, but there
are **no veterinary report templates** (no species-specific structured findings, no VHS field,
no signalment block). Report vocabulary is generic/human.

### 3.5 Compliance/audit surfaces
`credentials` app + `SecurityPage` carry human-healthcare compliance framing (HIPAA/PHI). For
veterinary data this is **inapplicable** (animals are property; no HIPAA). The audit-logging
*mechanics* are still valuable; the *claims and labels* are wrong.

---

## 4. External Landscape (what good veterinary platforms do)

### 4.1 Competitive features (Radimal, SignalPET, Vetology, PicoxIA, Antech)
- **Connect to existing X-ray/US/CT/MRI + PIMS** (practice-management systems). Integration and
  near-zero learning curve are decisive purchasing factors.
- **Workflow AI** (the defensible, high-value layer):
  - Automated **hanging protocols** / view layout
  - **Vertebral Heart Score (VHS)** auto-calculation **with trend tracking** over time
  - **Image-quality scoring** (positioning, exposure) at point of capture
  - **Worklist prioritization / critical-case detection** (e.g. obstruction, heart failure)
- **Hybrid AI + board-certified teleradiology**: instant AI draft, with specialist reports on
  **guaranteed turnaround** (SignalSTAT ~45 min; Radimal STAT ~35 min). "Free if late."
- **Point-of-care breadth**: SignalRAY reports **50+ findings** on companion-animal radiographs.
- **Adjacent products**: dental (SignalSMILE), chat/triage assistants (SignalCHAT).
- **Species focus**: overwhelmingly **canine + feline**, **radiography (X-ray) first**, then US/CT.

### 4.2 Clinical evidence — the cautionary core
A peer-reviewed comparison and an external-validation pilot (JAVMA) plus a *Frontiers*
commentary found commercial veterinary AI:
- **High specificity, low sensitivity** — overall sensitivity **0.688**, falling to **0.444** on
  complex multi-finding cases. It **misses real pathology**, the opposite of what a screening
  tool must do.
- Was validated on **small, single-institution, well-positioned, class-imbalanced** datasets
  (e.g. 84% normal — "calling everything normal scores 84%"), **without surgical/pathology
  ground truth**.
- Ships **without version numbers**, with **proprietary/opaque training data**, not adhering to
  **CLAIM** reporting or **FDA GMLP** principles → **not reproducible**.
- **AI does pattern recognition; radiologists do interpretation** (differentials, recommendations,
  clinical correlation). GPs **lack the expertise to catch AI errors → automation-bias risk.**

### 4.3 Regulatory reality
- **No FDA SaMD pathway** for veterinary AI; **state practice acts unenforced** against vendors;
  **no payer gatekeeping**. Products **illegal in human medicine operate at scale in vet med.**
- **2025 ACVR/ECVDI position statement**: *"no commercially available AI products for veterinary
  diagnostic imaging meet the required standards for transparency, validation, or safety"* and AI
  *"should always be used with a qualified veterinary professional in the loop."*
- **Critical legal line**: **measurement-style output** (VHS number, single flag) reads as an
  instrument ("just a tool"); **consultation-style prose** (impressions, differentials,
  recommendations) functions as a **diagnostic opinion** → unlicensed-practice exposure.
  **Liability flows to the referring veterinarian.**

---

## 5. Design Principles for VetImage

1. **Human-in-the-loop by default.** Never present AI output as a final diagnosis. Every AI
   result is a *draft / decision-support* artifact requiring veterinarian sign-off.
2. **Measurement & workflow before narrative.** Prioritize defensible, high-trust features
   (VHS, image-quality, triage flags, hanging protocols) over autonomous prose reads.
3. **Radical transparency.** Show model version, training/validation dataset, **sensitivity AND
   specificity**, confidence, and known limitations *at the point of result* (the registry
   already has the fields: `version`, `performance_metrics`, `validation_dataset`,
   `training_dataset`, `limitations`).
4. **Sensitivity-first messaging.** Surface "what the model may miss." Avoid "normal =
   confirmed." Default to flagging uncertainty.
5. **Species-aware everything.** Data model, taxonomy, models, templates, and stats must carry a
   species dimension (canine/feline first).
6. **Honest compliance.** Drop HIPAA/“Certified” claims. Animals aren't covered by HIPAA. State
   real posture: encryption, audit logging, access control, GDPR for *owner* PII only.
7. **Two audiences, two surfaces.** Veterinarians get the clinical workspace; pet owners get a
   simple, read-only, plain-language results/portal view (with explicit "ask your vet" framing).
8. **Open & reproducible.** Version models, record which model+version produced each result,
   adhere to CLAIM-style disclosure. This is also our differentiator vs. opaque incumbents.

---

## 6. Gap-Closure Roadmap (prioritized)

### Phase 1 — Make the veterinary data model real (foundational, do now)
- [x] **Run migrations**: `patients.0001_initial` + `dicom_images.0008_medicalstudy_animal_patient` applied.
- [x] **Wire Owner/Patient into the frontend**: `PatientsPage.tsx` (owner+animal CRUD, search,
      expandable list, signalment + study-timeline detail modal); nav link + `/patients` route;
      typed API client methods (`getOwners/createOwner/…`, `getAnimals/createAnimal/…`);
      org auto-provisioned lazily so new users can use the registry immediately. Tested
      (`patients/tests/test_api.py`, 6 passing).
- [x] **Study↔patient linking**: `PATCH /api/dicom/studies/{uid}` (`animal_patient_id`) +
      `apiClient.linkStudyToAnimal`; org-scoped; patient timeline reflects links.
- [ ] **Auto-link on upload**: map DICOM `patient_*` → suggest/create `AnimalPatient` *(follow-up —
      link API exists; upload-flow UI hook pending)*.
- [ ] **Species on study capture**: capture/confirm species at upload *(follow-up — drives model
      filtering once Phase 3 lands)*.

### Phase 2 — Fix safety/legal surfaces (low effort, high risk-reduction) ✅
- [x] **Rewrote `SecurityPage.tsx`** + `security` i18n (en/es/pt): removed HIPAA/SOC2 "Certified"
      badges; honest posture (TLS 1.3, AES-256, RBAC, audit trail, owner-PII GDPR); added a
      "Not a Medical Device / not FDA-cleared" card + a prominent **Responsible AI Use** banner.
- [x] **`AiDisclaimer` component** ("Decision support — not a diagnosis… vet must review… AI may
      miss findings") added to Analyze and Reports pages; i18n in 3 languages.
- [x] **Removed stray `LandingRef.tsx`**; fixed LandingPage "SOC 2 certified" bullet →
      "Owner-data privacy (GDPR)"; fixed stale `medai-platform.com` emails → `vetimage.app`.

### Phase 3 — Species-aware AI registry (clinical credibility) ✅
- [x] **Added `supported_species` (JSON)** to `ai_analysis.AIModel` (migration
      `0010`); list/detail serializers expose it; `AIModelViewSet.get_queryset`
      filters by `?species=` (species-agnostic models always match) and `?modality=`.
      ModelsPage gained a **Species** dropdown filter.
- [x] **Retire human-only models**: `seed_vet_models` management command deactivates
      MIRAGE/PI-CAI/CheXNet/FastSurfer/STU-Net/MIS-FM (`is_active=False`) — connectors kept,
      nothing deleted. Makefile `models-seed` now runs it; `models-seed-human` keeps the legacy seed.
- [x] **Seeded veterinary catalog entries** with honest metadata (supported_species, version,
      datasets, limitations, `experimental` flag): `vet-thorax-cr-v1` (canine/feline thoracic
      screening), `vet-vhs-v1` (VHS assistant), `vet-imgqc-v1` (image-quality, species-agnostic).
      No fabricated metrics — `performance_metrics` says "pending validation".
- [x] **Transparency block** on `ModelDetailsPage`: `AiDisclaimer` + species chips +
      Experimental badge; existing version/datasets/limitations sections retained; removed the
      misleading "all models validated" blurb on ModelsPage.

### Phase 4 — Flagship measurement feature: **Vertebral Heart Score (VHS)** ✅
The single highest-value, lowest-risk feature. It is a **measurement** (defensible), it's what
incumbents lead with, and it has clear clinical utility (cardiomegaly screening/monitoring).
- [x] **`VHSMeasurement` model** (`patients`, migration `0002`): long/short axis in vertebral
      units, **VHS computed server-side** (sum, can't drift), editable `landmark_points` JSON for
      re-opening, `method` (manual / ai_assisted-clinician-confirmed), `created_by`, source
      study/SOP UIDs. Species reference ranges (canine 8.5–10.6, feline 6.7–8.1) drive an
      `interpretation` (within/above/below range) — never a diagnosis.
- [x] **API**: `VHSMeasurementViewSet` (`/api/patients/vhs/`, org-scoped, `?animal=` filter);
      `AnimalPatient` detail returns chronological `vhs_trend`. Typed client methods.
- [x] **Trend tracking UI**: VHS panel in the patient detail — latest value + interpretation
      badge, recharts line chart with reference-range band, history list, and an add form that
      computes VHS live and carries the `AiDisclaimer`. Stored as **structured measurement, not
      prose**. Tested (`patients/tests/test_vhs.py`, 4 passing; 10 patients tests total).
- [ ] *Follow-up*: actual ML landmark auto-detection on the image (the `ai_assisted` method +
      `landmark_points` schema are in place as the hook; manual entry works today).

### Phase 5 — Veterinary reporting ✅
- [x] **Veterinary default templates** (`TemplateEngine` + `seed_report_templates`): "Veterinary
      Radiology Report", "Canine/Feline Thoracic (VHS)", "Veterinary General Report" — all with a
      **signalment** header (name/species/breed/sex/DOB/weight/owner), veterinary
      decision-support disclaimer, and `requires_signoff`.
- [x] **Report builder** enriches `patient_info` with signalment from a linked `AnimalPatient`
      (falls back to DICOM `patient_*`).
- [x] **Veterinarian sign-off**: `Report.approved_by`/`approved_at` (+ `is_approved`), migration
      `0003`; `POST /api/reports/{id}/approve` & `/unapprove` actions; serializer exposes status;
      ReportsPage gained an **Approve** button.
- [x] **PDF** (ReportLab): always-on veterinary disclaimer + a sign-off block (approver/date, or
      "DRAFT — awaiting veterinarian review").
- [x] Updated `report` fixture `patient_info` → animal signalment. Tests updated/added
      (31 reports tests passing, incl. sign-off + PDF).

### Phase 6 — Workflow & integrations (stickiness) — partial
- [x] **Worklist triage**: `AnalysisTask.priority` (routine / urgent / **STAT**), migration
      `0011`; settable on create (`CreateTaskSerializer` + view); exposed in list/detail/monitor
      serializers; WorklistTab **sorts STAT/urgent first** and shows a priority badge. Tested.
- [ ] **Hanging protocols** / default viewer layouts per modality+species — *follow-up*
      (needs OHIF layout-config plumbing).
- [ ] **PIMS integration** (ezyVet/Cornerstone/Avimark) + **DICOM MWL** on the gateway —
      *follow-up*: these require external systems/credentials not available in this
      environment; deferred rather than stubbed with fake behavior.
- [ ] **Teleradiology hand-off** — *follow-up*: priority + sign-off provide the workflow
      primitives; external routing needs a partner integration.

### Phase 7 — Pet-owner experience ✅
- [x] **Read-only owner portal** via secure share links: `Report.share_token`/`shared_at`
      (migration `0004`); `POST .../share` & `/unshare` actions; **sharing is gated to APPROVED
      reports** and auto-revoked on unapprove. Public `GET /api/reports/shared/<token>/`
      (`AllowAny`) returns a **sanitised** `PublicReportSerializer` (signalment + findings +
      summary + disclaimer + clinic — no internal IDs/model internals).
- [x] **`OwnerReportPage`** at public route `/shared/:token` (no login): plain-language summary
      with a "Reviewed by your veterinarian" banner and a "contact your clinic" prompt — framed as
      **explained by your veterinarian, never an AI verdict**. ReportsPage gained a **Share** button
      (approved reports only) that copies the owner link.
- [x] Tested: share-requires-approval, public access, revoke on unshare/unapprove (35 reports
      tests passing). Owner "auth" = unguessable token link (standard for results sharing).

### Cross-cutting — Remove/relabel human-medicine residue ✅ (mostly)
- [x] Relabelled user-facing human-medical copy → veterinary: auth placeholders
      (`doctor@hospital.com` → `vet@clinic.com`, "General Hospital" → "Your veterinary clinic"),
      dashboard/analyze/models titles ("Medical AI Dashboard" → "Veterinary Imaging Dashboard",
      etc.), and the anonymizer's inaccurate "PHI / Protected Health Information" →
      "identifying information (owner & patient)" across en/es/pt.
- [x] Kept the legitimate upstream **OpenMEDLab / Shanghai AI Laboratory** attribution and its
      `github.com/openmedlab/...` URLs (verified preserved).
- [ ] *Follow-up*: `StatisticsPage` species/modality/clinic/turnaround breakdowns — current
      labels are species-neutral and valid ("Patient" = the animal); a species/modality analytics
      re-frame needs backend aggregation by `AnimalPatient.species` and is deferred.

---

## Implementation status (2026-06)

Phases **1–5 and 7 complete**; Phase **6 partial** (worklist triage done; external
integrations deferred); cross-cutting **mostly done**. Backend: **332 tests passing**, 1
pre-existing unrelated failure (`test_create_task_incompatible_modality` — the create flow
intentionally soft-warns on modality mismatch rather than 400; stale assertion predates that
decision). Frontend typechecks clean for all touched files (two pre-existing `Authorization`
header warnings remain in `api.ts`). New migrations: `ai_analysis 0010/0011`,
`patients 0002`, `reports 0003/0004`.

---

## 7. Risk Register
| Risk | Severity | Mitigation |
|---|---|---|
| Presenting AI output as diagnosis (unlicensed-practice / liability) | **High** | Human-in-the-loop sign-off; measurement-first; persistent disclaimers (§5.1, §6 Phase 2) |
| False compliance claims (HIPAA "Certified") | **High** | Rewrite SecurityPage now (Phase 2) |
| Low-sensitivity AI giving false reassurance | **High** | Show sensitivity/limitations; "may miss" framing; never "normal = confirmed" |
| Phase-1 models unused / data model invisible | Medium | Wire frontend (Phase 1) — otherwise the vet pivot is cosmetic |
| Opaque models erode trust | Medium | Transparency block (version/datasets/metrics) — also our differentiator |
| Scope creep into teleradiology ops | Medium | Treat teleradiology as optional hand-off, not core, until core is solid |

---

## 8. Sources
- Radimal — board-certified reports + free PACS + AI: https://radimal.ai/
- Petfolk × Radimal teleradiology partnership: https://www.prnewswire.com/news-releases/petfolk-selects-radimal-as-exclusive-teleradiology-provider-for-its-national-veterinary-clinic-network-302449549.html
- SignalPET / Vetology / PicoxIA overview (Full Slice guide): https://fullslice.agency/blog/a-guide-to-ai-tools-for-veterinary-medicine/
- Vetology: https://vetology.net/ai/
- *Frontiers* Commentary — radiologists vs commercial AI (canine/feline): https://www.frontiersin.org/journals/veterinary-science/articles/10.3389/fvets.2025.1615947/full
- Original study (SignalPET-hosted) + PMC copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC11886591/
- JAVMA pilot — external validation deficiencies (canine abdomen): https://avmajournals.avma.org/view/journals/javma/aop/javma.25.10.0691/javma.25.10.0691.xml
- Veterinary AI regulatory gap / ACVR-ECVDI position analysis: https://veterinaryteleradiology.com/ai-primary-reads-veterinary-regulatory-gap/
- AI in veterinary radiology 2025 landscape (VOSD): https://www.vosd.in/ai-in-veterinary-radiology-and-diagnostic-imaging/

---

*This is a living document. Update §6 checkboxes as work lands; revise §4 as the market and the
ACVR/ECVDI guidance evolve.*
