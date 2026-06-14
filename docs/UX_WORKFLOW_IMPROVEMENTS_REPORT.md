# VetImage — UX, Workflow & Data-Handling Improvement Analysis

**Date:** 2026-06-07
**Status:** Review & recommendations (for prioritisation)
**Scope:** Frontend UX/UI, form quality, i18n, auth/session handling, the
owner→patient→study workflow, and data-security hardening.

---

## 1. Executive Summary

VetImage's foundations are solid: the Owner → AnimalPatient → Study data model is
live and tested, the AI registry is species-aware, reports support vet sign-off +
owner sharing, and both the component-test and OpenAPI/contract-test engines are
green. This review looks at the **next layer — day-to-day usability and data
integrity** — and finds a consistent theme: **several capabilities exist in the
backend/API but are not yet surfaced or hardened in the UI.**

The five highest-impact gaps:

1. **Study ↔ patient linking has no UI.** `apiClient.linkStudyToAnimal()` and the
   backend `PATCH /api/dicom/studies/{uid}` endpoint exist and are tested, but
   **no component calls them** — so a vet cannot actually attach an uploaded study
   to an animal patient from the viewer, study browser, or upload flow. This is the
   single biggest workflow gap.
2. **Partial i18n.** The patient registry forms, VHS panel, and the public
   owner report page are **hardcoded English**; there is no `patients` translation
   namespace. Spanish/Portuguese users (and pet owners) see English.
3. **Inconsistent form validation.** Auth forms use `react-hook-form` + `zod` with
   field-level errors; the Owner/Animal/VHS forms use ad-hoc `trim()` + toast with
   no inline errors, no email/phone/weight bounds, no microchip format.
4. **No geographic/data harmonisation.** `Owner.country` (and city) are free-text
   `CharField`s — inconsistent data, no validation, not selectable.
5. **No authentication rate-limiting.** Login and password-reset have no throttle
   or lockout — brute-force exposure.

Everything below is concrete, references the relevant files, and ends with a
prioritised roadmap (§10).

---

## 2. Form Validation (forms across the app)

**Current state**
- ✅ Auth forms (`LoginPage`, `RegisterPage`, `ForgotPasswordPage`,
  `ResetPasswordPage`) use `react-hook-form` + `zod` (`utils/validation.ts`) with
  inline field errors and strong password rules.
- ⚠️ `PatientsPage.tsx` Owner/Animal/VHS modals validate ad-hoc:
  `if (!form.first_name.trim()) toast.error(...)`. No inline errors, no email
  format check (the `<Input type="email">` only triggers native validation on a
  real `<form>` submit — these modals submit via a button click, so it never
  fires), no phone/weight/microchip validation.

**Problems**
- Inconsistent UX (some forms guide the user inline, others bail with a toast).
- Bad data can be saved: malformed emails, negative/implausible weights,
  free-form microchip IDs, future dates of birth.

**Recommendation**
- Reuse the existing `react-hook-form` + `zod` stack for the patient forms. Add
  `ownerSchema`, `animalPatientSchema`, `vhsSchema` to `utils/validation.ts`:
  - email (optional but validated), phone (E.164 via `libphonenumber-js`),
    `weight_kg` > 0 and < a sane max, `date_of_birth` not in the future,
    microchip 15-digit ISO-11784/11785 pattern (optional).
  - VHS axes: positive, plausible range (e.g. 2–8 vertebrae each).
- Surface errors with the existing `<Input error=...>` prop (already supported).
- Add server-side mirrors in DRF serializers (validation must not live only in the
  client) — e.g. `validate_weight_kg`, `validate_microchip_id`.

**Effort:** M · **Priority:** High (data integrity + consistency)

---

## 3. Country / Geographic Harmonisation

**Current state**
- `patients.Owner.country` and `.city` are free-text `CharField(max_length=...)`.
- Frontend renders a plain `<Input label="Country">` (`PatientsPage.tsx:113`).
- No country library installed (backend or frontend).

**Problems**
- "USA" / "U.S." / "United States" / "EEUU" all coexist → unsearchable,
  unreportable, inconsistent.

**Recommendation**
- **Backend:** add [`django-countries`](https://pypi.org/project/django-countries/)
  and switch `Owner.country` to `CountryField()` (stores ISO-3166 alpha-2). It
  ships localized country names (incl. es/pt) and a DRF serializer field.
- **Frontend:** replace the text input with a searchable select. Either:
  - a lightweight static ISO list + the existing select styling, or
  - `react-select` + `i18n-iso-countries` (localized labels per active language).
- Expose `GET /api/patients/countries/` (or embed the list) so the dropdown stays
  in sync with the backend.
- Optionally do the same for clinic locale/timezone on the Organization.

**Effort:** S–M · **Priority:** Medium

---

## 4. Internationalisation — Spanish & Portuguese Gaps

**Current state**
- 12 i18n namespaces exist for each of en/es/pt and the landing/auth/security/
  reports copy was translated in earlier phases.
- ❌ **`PatientsPage.tsx` forms are hardcoded English** ("First name", "Country",
  "Add VHS", species labels, all toasts). Only the page header uses `t()`.
- ❌ **No `patients` translation namespace** exists (`common.json` has no
  `patients` block beyond the nav label).
- ❌ **`OwnerReportPage.tsx` is 100% hardcoded English** — and it is the
  **owner-facing public page**, the one most likely to be read by a
  Spanish/Portuguese-speaking pet owner.
- ⚠️ The VHS panel, `AnimalDetailModal`, and species/sex option labels are English.

**Problems**
- The product advertises 3 languages but core clinical + owner-facing flows are
  English-only. The owner portal language gap is the most user-visible.

**Recommendation**
- Add a `patients` namespace (`en/es/pt`) covering: owner/animal/VHS form labels &
  placeholders, species & sex option labels, table headers, empty states, and all
  toasts. Convert `PatientsPage.tsx` to `t()`.
- Internationalise `OwnerReportPage.tsx` — and consider honouring a `?lang=`
  param on the share link (the clinic picks the owner's language when sharing).
- Add a CI check / script that diffs locale key sets across en/es/pt to catch
  missing keys going forward (a small `i18n:verify` script).

**Effort:** M · **Priority:** High (owner portal) / Medium (internal forms)

---

## 5. JWT Expiry & API-Call Auth Handling

**Current state**
- `SIMPLE_JWT`: 5-min access tokens, 7-day refresh, **`ROTATE_REFRESH_TOKENS` +
  `BLACKLIST_AFTER_ROTATION`** (good security posture). Refresh token in an
  HttpOnly cookie.
- Frontend (`utils/api.ts`): **reactive** refresh — a request that returns 401
  triggers a single refresh + retry, with a shared `tokenRefreshPromise` to avoid
  stampedes, and emits `auth:token-expired` on failure.

**Problems**
- Refresh is purely reactive: every ~5 minutes the *first* call fails with 401
  before the retry succeeds (extra latency, noisy logs, and any non-idempotent or
  non-retried call paths can surface a transient error to the user).
- No client-side awareness of token `exp`; no proactive refresh; no countdown or
  "session expiring" UX. WebSocket connections (monitoring) don't share the
  refresh lifecycle and can silently drop.

**Recommendation**
- Decode the access token `exp` (`jwt-decode`) and **proactively refresh** ~60s
  before expiry (timer in `AuthContext`/`apiClient`), keeping the 401 path as a
  fallback.
- Centralise: ensure *every* fetch goes through `apiClient.request()` (audit for
  any raw `fetch` — e.g. the uploader historically used a direct `fetch`).
- On refresh failure, route to login with a friendly "your session expired" toast
  (the `auth:token-expired` event already exists — make sure it's handled
  everywhere, incl. the WebSocket reconnect path).
- Consider lengthening the access token to 10–15 min to cut refresh churn while
  keeping rotation+blacklist for safety.

**Effort:** S–M · **Priority:** Medium

---

## 6. Patient (Animal) Registration Workflow

**Current state**
- Animals **are** registrable today — `PatientsPage.tsx` has an `AnimalFormModal`
  (species, breed, DOB, sex, weight, microchip, colour) reached by expanding an
  owner and clicking "+ Patient". Backend `AnimalPatientViewSet` + tests exist.
- Registration is **owner-first only**: you must create/find the owner, expand the
  row, then add the animal.

**Problems / opportunities**
- No patient-centric entry point: you can't start from "new patient" and
  create/attach the owner inline, nor search all animals across owners from one
  box (the registry search only filters owners).
- No quick "register patient during upload" path (see §7).
- Microchip — the natural unique key for an animal — isn't enforced unique or used
  for de-duplication / lookup.

**Recommendation**
- Add an **all-patients view/search** (by name, species, microchip, owner) backed
  by the existing `AnimalPatientViewSet` (it already supports `?species=`/`?owner=`
  and search) — surface microchip search prominently.
- Add a **"New patient"** flow that lets you pick an existing owner *or* create one
  inline (combobox + "create new").
- Enforce/scope **microchip uniqueness** within an organization and offer
  "patient already exists?" lookup before creating duplicates.

**Effort:** M · **Priority:** Medium

---

## 7. Study/Image ↔ Patient Association (highest-impact gap)

**Current state**
- Backend: `PATCH /api/dicom/studies/{uid}` with `{animal_patient_id}` exists,
  is org-scoped, and is **tested** (`patients/tests/test_api.py`).
- Client: `apiClient.linkStudyToAnimal()` exists and is typed.
- ❌ **No UI calls it.** A grep shows `linkStudyToAnimal` referenced only in the
  test mock — not in the viewer, `StudyBrowser`, uploader, or AnalyzePage.
- DICOM `patient_*` header fields are captured on upload, but nothing maps them to
  an `AnimalPatient`, and the patient timeline only shows links that were created
  via the API/admin.

**Problems**
- The core veterinary value — "see all of Rex's studies over time" — is unusable
  in practice because uploaded studies are never linked to a patient through the UI.
- VHS/report signalment enrichment (which keys off `study.animal_patient`) rarely
  fires.

**Recommendation** (pick the workflow that fits best; ideally both):
- **At upload:** after a study uploads, prompt "Assign to patient" — a searchable
  AnimalPatient picker (with "create new patient" inline). Auto-suggest a match
  from the DICOM `patient_name`/`patient_id`/microchip when present.
- **In the Study Browser / Viewer:** add an "Assign patient" / "Linked patient"
  control on each study (a small picker that calls `linkStudyToAnimal`), plus a
  visible "Patient: Rex (Canine)" chip when linked and "Unassigned" otherwise.
- **Reverse view:** the patient detail timeline already lists linked studies — make
  each entry deep-link into the viewer.
- **Backend assist:** an optional auto-link suggestion endpoint that proposes
  candidate patients from DICOM tags (the vet confirms — human-in-the-loop).

**Effort:** M–L · **Priority:** Highest (unlocks the platform's core workflow)

---

## 8. Data-Security Hardening

**Current state**
- ✅ CORS not wildcard; refresh token HttpOnly; SameSite=Lax; refresh rotation +
  blacklist; org-scoped querysets; audit logging exists (`credentials` app);
  anonymization tools present.
- ⚠️ `COOKIE_SECURE` defaults off (dev) — must be **on in production**.
- ❌ **No rate-limiting / lockout** on `login` or `password-reset` (no DRF
  throttles, no `django-axes`). Brute-force / credential-stuffing exposure.
- ⚠️ No explicit password-reset throttle or generic-response guarantee review.

**Recommendation**
- Add DRF throttling: `ScopedRateThrottle` on login/refresh/password-reset (e.g.
  5–10/min per IP), or adopt [`django-axes`](https://pypi.org/project/django-axes/)
  for account lockout + admin visibility.
- Enforce `COOKIE_SECURE=True` and `SECURE_SSL_REDIRECT`/HSTS in production
  settings (and document the prod env in the deployment guide).
- Ensure password-reset returns a generic message regardless of account existence
  (avoid user enumeration) and is throttled.
- Surface the existing audit log in the UI for clinic admins (who accessed which
  patient/report) — both a security and a trust feature for owner data.
- Add a short **data-retention / deletion** control for owner PII (GDPR), building
  on the existing anonymization tooling.

**Effort:** S (throttling/cookies) → M (audit UI, retention) · **Priority:** High
(throttling/cookies), Medium (rest)

---

## 9. Additional UX/UI Recommendations

- **Optimistic + loading/empty/error states:** standardise skeleton loaders and
  empty states (the registry and worklist already hint at this; make it a shared
  pattern). Disable submit buttons while saving (some modals do, not all).
- **Confirm destructive actions consistently:** owner/patient deletion uses
  `window.confirm` — replace with the existing `Modal` for a consistent, styled,
  translatable confirmation (and warn that deleting an owner cascades to patients).
- **Accessibility:** the earlier Role-select a11y fix was a good catch — sweep for
  unlabelled selects/inputs, focus traps in modals, and keyboard nav; add
  `aria-live` to toasts.
- **Patient signalment everywhere:** show the species/breed/age chip on study,
  report, worklist, and viewer headers once linking (§7) lands.
- **VHS UX:** allow editing an existing measurement (currently add/delete only) and
  show the trend delta vs. previous; add unit hints/diagram for axis measurement.
- **Global search:** a single command-bar to jump to an owner, patient (by
  microchip), or study.
- **Toasts → inline where appropriate:** validation belongs inline; reserve toasts
  for async outcomes.
- **Date/number/locale formatting:** use `Intl`/i18n-aware formatting for dates,
  weights, and VHS values per active language.

---

## 10. Prioritised Roadmap

| # | Improvement | Area | Impact | Effort | Priority | Status |
|---|---|---|---|---|---|---|
| 1 | **Wire study↔patient linking UI** (upload + viewer/browser) | Workflow | Unlocks core value | M–L | **Highest** | ✅ Done |
| 2 | Patient forms + OwnerReport i18n (es/pt) + `patients` namespace | i18n | Owner & clinic reach | M | **High** | ✅ Done |
| 3 | Zod validation for owner/animal/VHS forms (+ server mirrors) | Forms | Data integrity | M | **High** | ✅ Done |
| 4 | Auth rate-limiting/lockout + `COOKIE_SECURE` in prod | Security | Brute-force defense | S | **High** | ✅ Done |
| 5 | Country harmonisation (ISO-3166 select) | Data | Reporting/consistency | S–M | Medium | ✅ Done |
| 6 | Proactive JWT refresh (decode `exp`) + session-expiry UX | Auth | Fewer failed calls | S–M | Medium | ✅ Done |
| 7 | All-patients search + microchip uniqueness/dedup + "new patient" flow | Workflow | Registration UX | M | Medium | ✅ Done |
| 8 | Audit-log UI for clinic admins + PII retention controls | Security | Trust / GDPR | M | Medium | ✅ Done |
| 9 | UX polish (modals for confirms, a11y sweep, signalment chips, global search) | UI | Daily usability | M | Medium | ✅ Mostly |

### Implementation notes (2026-06)

- **#1 Study↔patient linking** — `StudyBrowser` now has a patient picker
  (`PatientPicker` + `AssignPatientModal`) and a linked-patient chip; the
  DICOMweb study list returns `AnimalPatientID/Name`; optimistic UI update.
- **#2 i18n** — new `patients` namespace (en/es/pt) covering all owner/animal/
  VHS forms, species/sex labels, toasts, the picker, and `OwnerReportPage`.
- **#3 Validation** — `ownerSchema`/`animalPatientSchema`/`vhsSchema` +
  `zodFieldErrors` with inline field errors; server-side mirrors
  (`validate_weight_kg`/`date_of_birth`/`microchip_id`/`country`).
- **#4 Security** — DRF `ScopedRateThrottle` on login/register/refresh/
  password-reset (env-tunable); production block enforces `SECURE_SSL_REDIRECT`,
  HSTS, secure session/CSRF/refresh cookies. Throttle test added; autouse
  cache-clear fixture prevents cross-test throttle bleed.
- **#5 Country** — `utils/countries.ts` (ISO-3166 codes + `Intl.DisplayNames`
  localized names) + `CountrySelect`; stores alpha-2; server validates the code.
- **#6 JWT** — `apiClient` decodes `exp` and proactively refreshes ~60s early
  (timer cancelled on logout); reactive 401 path retained; `auth:token-expired`
  redirects to `/auth/login?session=expired` with a friendly toast (fixed a
  pre-existing wrong `/login` redirect).
- **#7 Registration** — Owners/All-patients toggle; all-patients search (name/
  breed/microchip/owner); standalone "New patient" with inline `OwnerPicker`;
  microchip uniqueness enforced within the org.
- **#9 Polish** — `ConfirmDialog` replaces all `window.confirm`; submit buttons
  disabled while in-flight; signalment chip on studies; a11y labels on inputs/
  selects/buttons.
- **#8 Audit/PII** — `AuditLogPage` (admin-gated route `/audit-log` + nav link)
  showing the auth/access trail with event-type/date/suspicious filters;
  `AuditLogViewSet` broadened so clinic admins (role ≥ 3) see org-wide events
  (non-admins still scoped to their own). GDPR retention: `Owner.anonymize_pii()`
  (scrubs PII, keeps the record + study links), a `purge_expired_pii` management
  command honouring `OWNER_PII_RETENTION_DAYS` (env, 0 = off) with `--dry-run`/
  `--days`, plus owner-delete cascade and the existing DICOM anonymization tools.
  Tested (`patients/tests/test_pii_retention.py`).

### Quick wins — all delivered
`COOKIE_SECURE` in prod ✅ · login/reset throttle ✅ · `patients` i18n namespace
+ `PatientsPage` via `t()` ✅ · styled confirm modal ✅ · disable submit in-flight ✅

---

## 11. Notes on Method

Findings are grounded in the current code: `app/frontend/src/pages/PatientsPage.tsx`,
`OwnerReportPage.tsx`, `utils/api.ts`, `utils/validation.ts`,
`i18n/locales/*`, `app/backend/patients/`, and `backend/settings.py`
(`SIMPLE_JWT`, cookie/CORS config). The standout, verifiable gap is that
`linkStudyToAnimal` appears only in the API client and its test mock — no
production component invokes it — so the owner→patient→study chain cannot yet be
completed through the UI despite the backend supporting it.

*Living document — update as items land; cross-reference
`VETERINARY_ALIGNMENT_REPORT.md` for the broader clinical roadmap.*
