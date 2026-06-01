# OHIF Viewer Integration Plan

## Project Overview
Integrate OHIF Viewer v3.11.1 as a new "Tools" section in the MedAI Platform to enable visualization of:
- DICOM medical images (X-rays, CT, MRI, etc.)
- DICOM derivatives (SEG, RS, RT-STRUCT)
- Analysis results and reports overlaid on images

**Features:**
- Drag-and-drop DICOM file/folder upload
- Study browser with search functionality
- Full DICOM viewing capabilities via OHIF
- User-scoped access control
- Integration with existing medical AI workflow
- Analysis results overlay in viewer

---

## Architecture Decision: Embedded vs Separate Service

### Selected Approach: **Embedded OHIF in React Frontend**

**Rationale:**
1. **Simplified Deployment**: Single frontend container, no additional Docker service
2. **Unified Authentication**: Leverages existing AuthContext
3. **Consistent UI/UX**: Integrates with existing medical theme system
4. **Easier State Management**: Shared React context between main app and viewer
5. **Development Experience**: Hot-reload works seamlessly
6. **Network Simplicity**: No proxy configuration needed

**Trade-offs Accepted:**
- Larger frontend bundle size (acceptable for medical imaging application)
- OHIF updates require frontend rebuild (acceptable with CI/CD)

---

## Implementation Phases

### Phase 1: Frontend - OHIF Viewer Integration (Priority: HIGH)

#### 1.1 Install OHIF Dependencies
**Files:** `app/frontend/package.json`

Add OHIF packages:
```json
{
  "dependencies": {
    "@ohif/viewer": "3.11.1",
    "@ohif/core": "3.11.1",
    "@ohif/ui": "3.11.1",
    "@ohif/extension-default": "3.11.1",
    "@ohif/extension-cornerstone": "3.11.1",
    "@ohif/extension-cornerstone-dicom-sr": "3.11.1",
    "@ohif/extension-dicom-pdf": "3.11.1",
    "@ohif/extension-dicom-video": "3.11.1",
    "cornerstone-core": "^2.6.1",
    "cornerstone-tools": "^6.0.6",
    "cornerstone-wado-image-loader": "^4.1.3",
    "dicom-parser": "^1.8.13"
  }
}
```

**Additional utility libraries:**
```json
{
  "dependencies": {
    "file-saver": "^2.0.5"
  },
  "devDependencies": {
    "@types/file-saver": "^2.0.5"
  }
}
```

**Installation:**
```bash
docker exec frontend-xrays npm install
```

#### 1.2 Create OHIF Configuration
**New File:** `app/frontend/src/config/ohif.config.ts`

Configure OHIF with:
- Data source pointing to backend DICOM API
- Custom theme matching medical design
- Extension configuration
- Viewer modes (basic, segmentation, etc.)

#### 1.3 Create Tools/Viewer Page
**New File:** `app/frontend/src/pages/ToolsPage.tsx`

Layout structure:
- Top section: Drag-and-drop upload zone
- Middle section: File browser for uploaded studies
- Bottom/Modal: OHIF Viewer container

#### 1.4 Create OHIF Viewer Component
**New File:** `app/frontend/src/components/viewer/OHIFViewerContainer.tsx`

Responsibilities:
- Initialize OHIF Viewer with configuration
- Handle study loading
- Manage viewer lifecycle
- Theme integration

#### 1.5 Create Drag-and-Drop Upload Component
**New File:** `app/frontend/src/components/uploader/MedicalImageDropzone.tsx`

Features:
- Multi-file/folder drag-and-drop
- File type validation (DICOM only)
- Upload progress tracking
- Batch DICOM upload support
- File size limits (100 MB per file)
- User storage quota tracking (5 GB)

**Supported formats:**
- DICOM (.dcm, .dicom)

#### 1.6 Create Study Browser Component
**New File:** `app/frontend/src/components/viewer/StudyBrowser.tsx`

Features:
- List uploaded studies with metadata
- Search/filter functionality
- Study preview cards
- Click to open in OHIF Viewer

#### 1.7 Update Routing
**File:** `app/frontend/src/App.tsx`

Add new route:
```tsx
<Route
  path="/tools"
  element={
    <ProtectedRoute>
      <ToolsPage />
    </ProtectedRoute>
  }
/>
```

#### 1.8 Update Navigation
**File:** `app/frontend/src/components/navbars/Navbar.tsx`

Add to navigation array:
```tsx
const navigation = [
  { name: 'Models', href: '/models', icon: Brain },
  { name: 'Analysis', href: '/analyze', icon: FileText },
  { name: 'Tools', href: '/tools', icon: Microscope }, // NEW
  { name: 'Documentation', href: '/docs', icon: FileText },
  { name: 'Security', href: '/security', icon: Shield },
];
```

#### 1.9 Create API Client Utilities
**New File:** `app/frontend/src/utils/api.ts`

Centralized API configuration:
- Environment-based API URL
- Typed API methods for DICOM operations
- Error handling wrapper
- Authentication header injection

#### 1.10 Update Vite Configuration
**File:** `app/frontend/vite.config.ts`

Enable proxy for DICOM API:
```ts
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://backend-xrays:3080',
        changeOrigin: true,
      }
    }
  },
  optimizeDeps: {
    include: ['@ohif/viewer', '@ohif/core', '@ohif/ui']
  }
})
```

---

### Phase 2: Backend - DICOM API Implementation (Priority: HIGH)

#### 2.1 Create DICOM Images App
**Command:**
```bash
docker exec backend-xrays python manage.py startapp dicom_images
```

**Add to settings:**
```python
INSTALLED_APPS = [
    # ...
    'dicom_images',
]
```

#### 2.2 Install Python Dependencies
**File:** `app/backend/setup/requirements.txt`

Add:
```
pydicom==2.4.4
numpy==1.24.3
Pillow==10.1.0
python-dateutil==2.8.2
django-filter==23.5
```

**Install:**
```bash
docker exec backend-xrays pip install -r setup/requirements.txt
```

#### 2.3 Create Database Models
**New File:** `app/backend/dicom_images/models.py`

Models:
- `MedicalStudy` - Study-level DICOM metadata
- `MedicalSeries` - Series within a study
- `MedicalImage` - Individual DICOM instances
- `AnalysisResult` - AI analysis results linked to images

Fields include:
- DICOM UIDs (StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID)
- Patient metadata (anonymized)
- Modality, acquisition date
- File storage paths
- User ownership
- Timestamps

#### 2.4 Create Serializers
**New File:** `app/backend/dicom_images/serializers.py`

Serializers:
- `MedicalImageSerializer` - Single image
- `MedicalSeriesSerializer` - Series with nested images
- `MedicalStudySerializer` - Study with nested series
- `DicomUploadSerializer` - File upload validation

#### 2.5 Implement DICOMweb-Compatible Views
**New File:** `app/backend/dicom_images/views.py`

Views following DICOMweb WADO-RS standard:
- `StudyListView` - GET /dicom-web/studies
- `SeriesListView` - GET /dicom-web/studies/{studyUID}/series
- `InstanceListView` - GET /dicom-web/studies/{studyUID}/series/{seriesUID}/instances
- `InstanceRetrieveView` - GET /dicom-web/studies/{studyUID}/series/{seriesUID}/instances/{sopUID}
- `FrameRetrieveView` - GET frame data for rendering
- `DicomUploadView` - POST upload endpoint
- `StudySearchView` - Search with filters

#### 2.6 Create URL Configuration
**New File:** `app/backend/dicom_images/urls.py`

Routes:
```python
urlpatterns = [
    # DICOMweb endpoints (OHIF compatible)
    path('dicom-web/studies', StudyListView.as_view()),
    path('dicom-web/studies/<str:study_uid>/series', SeriesListView.as_view()),
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/instances', InstanceListView.as_view()),
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/instances/<str:sop_uid>', InstanceRetrieveView.as_view()),

    # Upload and management
    path('upload/', DicomUploadView.as_view()),
    path('studies/', StudySearchView.as_view()),
]
```

**Update main URLs:**
```python
# backend/urls.py
urlpatterns = [
    # ...
    path('api/dicom/', include('dicom_images.urls')),
]
```

#### 2.7 Update Settings for Media Files
**File:** `app/backend/backend/settings.py`

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# DICOM-specific settings
DICOM_STORAGE_PATH = MEDIA_ROOT / 'dicom'
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB per file
USER_STORAGE_QUOTA = 5 * 1024 * 1024 * 1024  # 5 GB per user
ALLOWED_DICOM_EXTENSIONS = ['.dcm', '.dicom']
```

#### 2.8 Update Docker Volumes
**File:** `docker-compose.yml`

Add media volume:
```yaml
backend-xrays:
  volumes:
    - ./app/backend:/var/www/app/backend
    - ./data/media:/var/www/app/backend/media  # NEW
    - shared_volume:/var/www/static
```

Create directory:
```bash
mkdir -p data/media/dicom
```

#### 2.9 Run Migrations
```bash
docker exec backend-xrays python manage.py makemigrations dicom_images
docker exec backend-xrays python manage.py migrate
```

---

### Phase 3: Integration & Features (Priority: MEDIUM)

#### 3.1 Implement File Upload Handler
**Component:** `MedicalImageDropzone.tsx`

Flow:
1. User drops files/folders
2. Client-side validation (file type, size)
3. Parse DICOM metadata using `dicom-parser`
4. Create FormData with files + metadata
5. Upload to `/api/dicom/upload/` with progress tracking
6. Display success/error toast notifications
7. Refresh study browser

#### 3.2 Implement Study Search
**Component:** `StudyBrowser.tsx`

Features:
- Search by patient ID, study date, modality
- Filter by date range
- Sort by upload date, study date
- Pagination for large datasets
- Click study to open in OHIF Viewer

#### 3.3 OHIF Viewer Initialization
**Component:** `OHIFViewerContainer.tsx`

Initialization:
1. Load OHIF configuration
2. Set data source to backend API
3. Pass study UID to load
4. Initialize extensions (cornerstone, segmentation)
5. Apply medical theme colors
6. Handle viewer events

#### 3.4 Analysis Results Integration
**New Model:** `AnalysisResult` in `dicom_images/models.py`

Links AI analysis outputs to medical images:
- Segmentation masks (DICOM SEG)
- Structured reports (DICOM SR)
- RT structures
- Confidence scores
- Annotations

**Frontend:** Display analysis results overlay in OHIF Viewer using DICOM SEG format

---

### Phase 4: Testing & Documentation (Priority: MEDIUM)

#### 4.1 Create Sample DICOM Dataset
**Directory:** `app/backend/fixtures/sample_dicom/`

Include:
- Sample chest X-ray DICOM
- Sample CT series (multi-slice)
- Sample segmentation
- Anonymized metadata

#### 4.2 Write API Documentation
**File:** `docs/API.md`

Document:
- All DICOM endpoints
- Request/response formats
- Authentication requirements
- Upload procedures
- Error codes

#### 4.3 User Guide
**File:** `docs/USER_GUIDE_TOOLS.md`

Sections:
- How to upload DICOM files
- How to browse studies
- How to use OHIF Viewer
- Supported file formats
- Troubleshooting

#### 4.4 Testing
Create tests for:
- DICOM upload validation
- Metadata extraction
- API endpoints
- File type handling
- Error cases

---

## File Structure Summary

```
app/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── uploader/
│   │   │   │   ├── ImageUploader.tsx (existing)
│   │   │   │   └── MedicalImageDropzone.tsx (NEW)
│   │   │   └── viewer/
│   │   │       ├── OHIFViewerContainer.tsx (NEW)
│   │   │       └── StudyBrowser.tsx (NEW)
│   │   ├── pages/
│   │   │   └── ToolsPage.tsx (NEW)
│   │   ├── config/
│   │   │   └── ohif.config.ts (NEW)
│   │   └── utils/
│   │       └── api.ts (NEW - centralized API)
│   ├── package.json (UPDATE)
│   └── vite.config.ts (UPDATE)
│
└── backend/
    ├── dicom_images/ (NEW APP)
    │   ├── models.py
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   └── migrations/
    ├── backend/
    │   ├── settings.py (UPDATE)
    │   └── urls.py (UPDATE)
    └── setup/
        └── requirements.txt (UPDATE)

data/
└── media/ (NEW)
    └── dicom/

docs/
├── OHIF_INTEGRATION_PLAN.md (this file)
├── API.md (NEW)
└── USER_GUIDE_TOOLS.md (NEW)
```

---

## Dependencies Summary

### Frontend
```json
{
  "@ohif/viewer": "3.11.1",
  "@ohif/core": "3.11.1",
  "@ohif/ui": "3.11.1",
  "@ohif/extension-default": "3.11.1",
  "@ohif/extension-cornerstone": "3.11.1",
  "cornerstone-core": "^2.6.1",
  "dicom-parser": "^1.8.13",
  "file-saver": "^2.0.5"
}
```

### Backend
```txt
pydicom==2.4.4
numpy==1.24.3
Pillow==10.1.0
python-dateutil==2.8.2
django-filter==23.5
```

---

## Implementation Order

1. **Phase 1.1-1.9**: Frontend structure and routing (1-2 days)
2. **Phase 2.1-2.9**: Backend DICOM API (2-3 days)
3. **Phase 3.1-3.2**: File upload and study browser (1-2 days)
4. **Phase 3.3**: OHIF Viewer integration (2-3 days)
5. **Phase 3.4**: Analysis results overlay (1-2 days)
6. **Phase 4**: Testing and documentation (1-2 days)

**Total Estimated Effort:** 8-14 days

---

## Risk Mitigation

### Risk 1: OHIF Bundle Size Impact
**Mitigation:**
- Lazy load OHIF Viewer on Tools page
- Code splitting with React.lazy
- Tree-shaking unused OHIF extensions

### Risk 2: DICOM Parsing Performance
**Mitigation:**
- Background processing for large uploads
- Celery task queue for metadata extraction
- Progress indicators for user feedback

### Risk 3: Cross-Origin Issues
**Mitigation:**
- CORS already enabled in backend
- Use API proxy in Vite for development
- Ensure proper content-type headers

### Risk 4: Large File Uploads
**Mitigation:**
- Chunked upload support
- Upload size limits in settings
- Progress tracking and resumable uploads

---

## Success Criteria

1. Users can drag-and-drop DICOM files to upload
2. Uploaded studies appear in study browser (user-scoped)
3. Clicking a study opens OHIF Viewer
4. OHIF Viewer correctly renders DICOM images
5. Multi-frame/series navigation works
6. Search functionality finds studies by metadata
7. File size limits enforced (100 MB per file)
8. User storage quota enforced (5 GB total)
9. Mobile/tablet responsive design
10. Dark/light theme consistency
11. Authentication protects DICOM access
12. Analysis results overlay on images

---

## Future Enhancements (Post-MVP)

- Real-time collaboration (multiple viewers)
- Annotations and measurements export
- PACS integration
- HL7/FHIR support
- Advanced segmentation tools
- 3D volume rendering
- Hanging protocols
- Worklists
- Report generation from viewer
- AI model integration directly in viewer

---

## Implementation Decisions (User Confirmed)

### Decision 1: File Format Support
**DICOM Only** - Focus on DICOM compatibility exclusively. No NIfTI support needed (OHIF v3.11 doesn't have native NIfTI support).

### Decision 2: Analysis Results Display
**Overlay in OHIF Viewer** - Display segmentation masks and annotations directly on images within the viewer using DICOM SEG/SR format.

### Decision 3: Access Control
**User-scoped** - Users can only view their own uploaded studies. Simplest implementation with good privacy for development phase.

### Decision 4: Storage Limits
**Development Limits:**
- Maximum file size per upload: 100 MB
- Total storage per user: 5 GB
- These limits can be adjusted later based on production requirements

---

## Notes
- OHIF v3.11.1 is stable and production-ready
- DICOMweb WADO-RS standard ensures interoperability
- Existing authentication and theming can be reused
- Docker setup supports hot-reload for rapid development
