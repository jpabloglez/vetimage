# OpenMedLab - Project Roadmap

> **Last updated:** 2026-02-14
> **Status:** Active Development
> **Branch:** `dev` (integration) / `main` (stable releases)

---

## Current State Summary

OpenMedLab is a containerized DICOM data management platform built with Django 5 + DRF (backend), React 18 + TypeScript (frontend), and supporting microservices (DICOM Gateway, AI Orchestrator). The system currently provides:

- **DICOM management** with DICOMweb compliance (QIDO-RS, WADO-RS)
- **Multi-format uploads** (DICOM, NIfTI, JPEG, PNG)
- **Medical image visualization** via OHIF Viewer and Cornerstone.js
- **AI analysis orchestration** through a gRPC-based orchestrator with Redis job queue
- **DICOM Gateway** (Phase 1 POC) for receiving images from PACS systems
- **Authentication & security** with JWT, session tracking, audit logging, and brute force protection
- **Real-time monitoring** via polling (WebSocket optional)
- **12 Docker services** including PostgreSQL, Redis, Celery workers, and Orthanc test PACS

---

## Roadmap Phases

### Phase 1 - Stabilization & Testing (Current)

**Goal:** Harden the existing foundation before adding new capabilities.

| Area | Task | Priority |
|------|------|----------|
| Testing | Add unit tests for `dicom_images`, `ai_analysis`, and `credentials` apps | High |
| Testing | Add integration tests for DICOMweb endpoints (QIDO-RS, WADO-RS) | High |
| Testing | Frontend component tests with Vitest for critical pages (Analyze, Monitor) | High |
| Testing | End-to-end tests for upload-to-analysis workflow | Medium |
| Auth | Validate refresh token rotation edge cases and session cleanup | High |
| Auth | Finalize password reset flow (forgot/reset pages exist, verify backend) | Medium |
| Gateway | Stress-test DICOM SCP under concurrent C-STORE associations | Medium |
| Orchestrator | Verify gRPC reconnection and retry logic under failure scenarios | Medium |
| DevOps | Add health check endpoints for all services in Docker Compose | Medium |
| DevOps | CI pipeline setup (lint, test, build) | High |

---

### Phase 2 - Supported Models & AI Capabilities

**Goal:** Expand the AI model ecosystem and make analysis results actionable.

| Area | Task | Priority | Status |
|------|------|----------|--------|
| Models | Integrate MIRAGE model for medical image report generation | High | ✅ Done (Phase 1) |
| Models | Integrate PICAI model for prostate cancer detection on MRI | High | ✅ Done — connector completed with modality validation + gRPC payload |
| Models | Add chest X-ray classification model (e.g., CheXNet or TorchXRayVision) | Medium | ✅ Done — CheXNet connector + seed data |
| Models | Add segmentation model support (organ/lesion segmentation with mask overlay) | Medium | |
| Models | Model versioning system - track model versions and allow rollback | Medium | |
| Registry | Expand `AIModel` registry with metadata: input modalities, body regions, performance metrics | High | ✅ Done (Phase 1) |
| Registry | Model compatibility validation (check modality/series before submission) | Medium | ✅ Done — serializer + frontend compatibility warning |
| Orchestrator | Support GPU-accelerated inference via EC2 launcher (`ec2_launcher.py` exists) | Low | |
| Orchestrator | Model warm-up and caching for frequently used models | Low | |

---

### Phase 3 - Tools & Reporting

**Goal:** Provide clinical-grade tools and structured reporting capabilities.

| Area | Task | Priority | Status |
|------|------|----------|--------|
| Tools | DICOM anonymization tool (batch PHI removal for research datasets) | High | Done — 3 profiles (basic/full/research), Celery background jobs, ZIP download |
| Tools | DICOM tag editor (view/modify metadata before re-upload) | Medium | Done — DicomTagEditorService with search, inline editing, restricted-tag protection, 8 tests |
| Tools | Format conversion tool (DICOM to NIfTI, DICOM to PNG/JPEG) | Medium | Done — ConversionJob + Celery task, JPEG/PNG via dicom_to_image, NIfTI via nibabel, 10 tests |
| Tools | Batch operations - multi-study selection for export, delete, or analysis | Medium | Done — BatchJob model, export ZIP / bulk delete / bulk analyze, 10 tests |
| Reporting | Structured report generation from AI analysis results | High | Done — ReportBuilder service with structured JSON content |
| Reporting | PDF report export with findings, annotated images, and model confidence scores | High | Done — PDFReportGenerator with reportlab, professional medical styling |
| Reporting | Report templates system (customizable per institution/use case) | Medium | Done — ReportTemplate model, TemplateEngine, 3 defaults (radiology/pathology/general), seed command, 11 tests |
| Reporting | Report comparison - side-by-side view of multiple analyses on same study | Low | Done — LCS-based diff hook, side-by-side viewer, study_uid filter on reports API |
| Reporting | Audit trail report generator for compliance reviews | Medium | Done — AuditReportService with filters, structured JSON + PDF export via PDFReportGenerator, 9 tests |

---

### Phase 4 - Data Analysis & Improved UI

**Goal:** Deliver dashboards, analytics, and a polished user experience.

| Area | Task | Priority | Status |
|------|------|----------|--------|
| Analytics | Statistics dashboard enhancements - modality distribution, upload trends, storage usage over time | High | Done — study_analytics endpoint, ModalityDistributionChart, UploadTrendsChart, StorageUsageChart |
| Analytics | Per-model performance metrics (accuracy, processing time, failure rates) | High | Done — ModelMetricsViewSet, ModelPerformanceChart, ModelTrendsChart |
| Analytics | User activity analytics (studies uploaded, analyses run, storage consumed) | Medium | Done — UserActivityViewSet, UserActivityTable, MyActivityCard |
| Analytics | Population-level insights (age/gender distribution, common findings) | Low | Done — population endpoint, PopulationInsightsPanel with age/gender/findings charts |
| UI | Redesign AnalyzePage with drag-and-drop upload and progress indicators | High | Done — DragDropUploadZone, AnalysisProgressTracker |
| UI | Study list view with sortable columns, pagination, and inline previews | High | Done — StudyTableView with sortable columns, ViewToggle grid/table switch |
| UI | Dark mode support across all pages | Medium | Done — audited and ensured dark: classes across all new and existing components |
| UI | Responsive/mobile-friendly layout for monitoring and study browsing | Medium | Done — responsive grid breakpoints, mobile-friendly cards |
| UI | Notification system (in-app alerts for completed analyses, errors) | Medium | Done — Notification model, NotificationViewSet, NotificationBell + NotificationDropdown, Celery hooks |
| UI | Keyboard shortcuts for viewer navigation and common actions | Low | Done — useKeyboardShortcuts hook, KeyboardShortcutsHelp modal (press ?) |
| Viewer | Enhance OHIF integration - custom toolbar buttons for AI analysis triggers | Medium | Done — AIToolbarButton in viewer header |
| Viewer | Multi-planar reconstruction (MPR) for volumetric datasets | Low | Done — MPRViewer three-panel layout with slice sliders |
| Viewer | Side-by-side comparison view for prior/current studies | Medium | Done — ComparisonViewer with sync controls, StudyComparisonSelector |

---

### Phase 5 - Documentation & Code Optimization

**Goal:** Comprehensive documentation and maintainable, performant codebase.

| Area | Task | Priority |
|------|------|----------|
| Docs | API documentation review - ensure all endpoints documented in drf-spectacular | High |
| Docs | User guide with screenshots for common workflows | High |
| Docs | Architecture decision records (ADRs) for key choices (gRPC, Celery, OHIF) | Medium |
| Docs | Deployment guide (production setup with Nginx, SSL, environment variables) | High |
| Docs | Developer onboarding guide (local setup, contributing guidelines) | Medium |
| Code | Consolidate archived docs in `docs/tasks/` - extract actionable items, archive the rest | Medium |
| Code | Database query optimization - add `select_related`/`prefetch_related` where missing | High | ✅ Done — select_related on 8 ViewSets, bulk aggregates in analytics |
| Code | API response pagination audit (ensure consistent pagination across all list endpoints) | Medium | ✅ Done — global PAGE_SIZE=50, explicit pagination_class on all list ViewSets |
| Code | Frontend code splitting and lazy loading for page components | Medium |
| Code | Extract shared TypeScript types/interfaces for API responses | Medium |
| Code | Backend logging standardization (structured JSON logging for production) | Medium |
| Code | Redis connection pooling and cache strategy review | Low |
| Code | Remove dead code and unused dependencies from both `requirements.txt` and `package.json` | Low |

---

### Phase 6 - Advanced Features & Integrations

**Goal:** Enterprise-grade capabilities for broader adoption.

| Area | Task | Priority |
|------|------|----------|
| FHIR | FHIR R4 resource mapping for interoperability with EHR systems | Medium |
| Multi-tenancy | Organization-level data isolation and admin panels | Medium |
| RBAC | Fine-grained permissions per study, series, and model access | High |
| Gateway | DICOM Gateway Phase 2 - query/retrieve (C-FIND/C-MOVE) from external PACS | Medium |
| Gateway | Routing rules engine (auto-forward studies matching criteria to AI models) | Medium |
| Storage | S3-compatible object storage backend for media files | Medium |
| Monitoring | Prometheus + Grafana dashboards for system observability | Low |
| Scaling | Horizontal scaling support for Celery workers and orchestrator | Low |
| i18n | Internationalization support (Spanish, Portuguese as initial targets) | Low |

---

## Versioning Plan

| Version | Phase | Milestone |
|---------|-------|-----------|
| **0.1.x** | Phase 1 | Test coverage > 70%, CI pipeline active |
| **0.2.x** | Phase 2 | 3+ AI models integrated and functional |
| **0.3.x** | Phase 3 | Reporting system with PDF export |
| **0.4.x** | Phase 4 | Redesigned UI with analytics dashboards |
| **0.5.x** | Phase 5 | Full documentation, optimized codebase |
| **1.0.0** | Phase 6 | Feature-complete platform release |

---

## Contributing

Each task above maps to a potential issue or PR. When picking up work:

1. Create a branch from `dev` following the pattern `OMLAB-XXX/short-description`
2. Reference the roadmap phase and task in commit messages
3. Ensure tests pass before opening a PR against `dev`
4. Update this roadmap when tasks are completed or priorities shift

---

## Notes

- This roadmap is a living document and will evolve as requirements are refined
- Priorities may shift based on user feedback and operational needs
- The platform is for **educational/research purposes** - clinical use requires proper certification and regulatory compliance
