# TASK: Complete OHIF Viewer Integration

**Status**: Vertical Slice Complete - Full Integration Pending
**Priority**: High
**Complexity**: High
**Dependencies**: OHIF Viewer v3.11.1, Cornerstone Libraries, DICOMweb Backend

---

## Executive Summary

The vertical slice implementation has successfully demonstrated the complete workflow from DICOM upload → storage → browse → view. The backend DICOMweb API is functional, and the frontend infrastructure is in place. The next phase involves replacing the viewer placeholder with the full OHIF Viewer implementation to enable advanced medical image viewing, manipulation, and analysis capabilities.

---

## Current State (Completed ✅)

### Backend Infrastructure
- ✅ Django `dicom_images` app with complete data models
- ✅ DICOMweb QIDO-RS compatible endpoints
  - Studies listing: `GET /api/dicom/dicom-web/studies`
  - Series listing: `GET /api/dicom/dicom-web/studies/{uid}/series`
  - Instances listing: `GET /api/dicom/dicom-web/studies/{uid}/series/{uid}/instances`
- ✅ DICOM file upload with pydicom metadata extraction
- ✅ User-scoped access control
- ✅ Storage quota management (100MB/file, 5GB/user)
- ✅ Database models: MedicalStudy, MedicalSeries, MedicalImage, UserStorageQuota
- ✅ File storage in `/media/dicom/` with organized structure

### Frontend Infrastructure
- ✅ OHIF packages installed (v3.11.1)
- ✅ OHIF configuration file (`src/config/ohif.config.ts`)
- ✅ DicomDropzone component with drag-and-drop upload
- ✅ StudyBrowser component with search and filtering
- ✅ ToolsPage with tabbed interface
- ✅ API client with typed methods
- ✅ Routing and navigation configured
- ✅ Vite proxy for API requests
- ✅ Placeholder viewer showing study metadata

### What Works
- Users can upload DICOM files via drag-and-drop
- Metadata is automatically extracted and stored
- Studies are listed with search functionality
- Study details and series information are displayed
- Storage quotas are tracked and enforced
- All components render correctly

---

## Gaps Requiring Implementation

### Critical (Blocking Full Viewer)
1. **WADO-RS Pixel Data Endpoints** - OHIF needs to retrieve actual image pixel data
2. **DICOM Frame Serving** - Convert stored DICOM files to viewable formats
3. **OHIF Viewer Component Integration** - Replace placeholder with real viewer
4. **Extension Configuration** - Enable Cornerstone, measurement tools, segmentation

### Important (Enhanced Functionality)
5. **Multi-frame Image Support** - Handle DICOM files with multiple frames
6. **Image Caching** - Improve performance for repeated access
7. **Viewport Presets** - Window/level presets for different modalities
8. **Hanging Protocols** - Automatic layout configuration based on study type

### Nice-to-Have (Future Enhancements)
9. **3D Rendering** - MPR, VR for CT/MRI volumes
10. **AI Analysis Integration** - Display model predictions as overlays
11. **DICOM SR Display** - Structured report viewing
12. **Comparison Mode** - Side-by-side study comparison

---

## Implementation Plan

### Phase 1: WADO-RS Backend Implementation (High Priority)

#### 1.1 Add WADO-RS Endpoints

**File**: `app/backend/dicom_images/views.py`

Create new view classes:

```python
class WADORSInstanceRetrieveView(APIView):
    """
    WADO-RS Instance Retrieve
    GET /api/dicom/dicom-web/studies/{studyUID}/series/{seriesUID}/instances/{sopUID}

    Returns: DICOM file or rendered frames
    Accept: application/dicom, image/jpeg, image/png
    """

class WADORSFrameRetrieveView(APIView):
    """
    WADO-RS Frame Retrieve
    GET /api/dicom/dicom-web/studies/{studyUID}/series/{seriesUID}/instances/{sopUID}/frames/{frameNumber}

    Returns: Individual frame as JPEG/PNG
    Accept: image/jpeg, image/png, application/octet-stream
    """

class WADORSMetadataRetrieveView(APIView):
    """
    WADO-RS Metadata Retrieve
    GET /api/dicom/dicom-web/studies/{studyUID}/metadata

    Returns: Complete DICOM metadata in JSON format
    """
```

**Key Implementation Details**:
- Use `pydicom` to read stored DICOM files
- Extract pixel data from DICOM instances
- Convert to JPEG/PNG using `Pillow`
- Handle windowing (window center/width) from request parameters
- Apply proper DICOM transformations (modality LUT, VOI LUT)
- Support multi-frame extraction
- Return appropriate Content-Type headers
- Implement proper error handling for missing/corrupt files

**Additional Dependencies Needed**:
```txt
pylibjpeg==2.1.0  # For JPEG 2000 support in DICOM
pylibjpeg-libjpeg==2.1.0  # JPEG baseline support
python-gdcm==3.0.22  # For advanced DICOM codecs (optional)
```

#### 1.2 Update URL Configuration

**File**: `app/backend/dicom_images/urls.py`

Add new routes:
```python
urlpatterns = [
    # ... existing routes ...

    # WADO-RS endpoints
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/instances/<str:sop_uid>',
         WADORSInstanceRetrieveView.as_view(), name='wadors-instance'),
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/instances/<str:sop_uid>/frames/<int:frame_number>',
         WADORSFrameRetrieveView.as_view(), name='wadors-frame'),
    path('dicom-web/studies/<str:study_uid>/metadata',
         WADORSMetadataRetrieveView.as_view(), name='wadors-metadata'),
]
```

#### 1.3 Implement Image Processing Utilities

**New File**: `app/backend/dicom_images/utils.py`

```python
def dicom_to_image(dcm, frame_number=0, window_center=None, window_width=None):
    """
    Convert DICOM pixel data to PIL Image

    Args:
        dcm: pydicom Dataset
        frame_number: Frame index for multi-frame images
        window_center: Window center for windowing
        window_width: Window width for windowing

    Returns:
        PIL Image object
    """

def apply_windowing(pixel_array, window_center, window_width):
    """Apply windowing (contrast adjustment) to pixel array"""

def apply_modality_lut(pixel_array, dcm):
    """Apply modality LUT transformation"""

def get_default_window_presets(modality):
    """Get default window/level presets for modality (CT, MR, etc.)"""
```

#### 1.4 Add Django Settings for Image Processing

**File**: `app/backend/backend/settings.py`

```python
# Image rendering settings
IMAGE_RENDER_FORMAT = 'JPEG'  # or 'PNG'
IMAGE_RENDER_QUALITY = 90  # JPEG quality (1-100)
IMAGE_MAX_DIMENSION = 2048  # Max width/height for rendered images
ENABLE_IMAGE_CACHE = True
IMAGE_CACHE_TIMEOUT = 3600  # Cache for 1 hour
```

---

### Phase 2: Frontend OHIF Viewer Integration (High Priority)

#### 2.1 Create OHIF Viewer Component

**New File**: `app/frontend/src/components/viewer/OHIFViewer.tsx`

Replace the placeholder with actual OHIF integration:

```typescript
import React, { useEffect, useRef } from 'react';
import { CommandsManager, ExtensionManager, ServicesManager } from '@ohif/core';
import { OHIFCornerstoneViewport } from '@ohif/extension-cornerstone';
import ohifConfig, { extensionConfig } from '../../config/ohif.config';

interface OHIFViewerProps {
  studyInstanceUIDs: string[];
  onClose?: () => void;
}

export const OHIFViewer: React.FC<OHIFViewerProps> = ({ studyInstanceUIDs, onClose }) => {
  const viewerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initialize OHIF Viewer
    initializeViewer();

    return () => {
      // Cleanup viewer
      cleanupViewer();
    };
  }, [studyInstanceUIDs]);

  const initializeViewer = async () => {
    // 1. Create managers
    const commandsManager = new CommandsManager();
    const servicesManager = new ServicesManager();
    const extensionManager = new ExtensionManager({ commandsManager, servicesManager });

    // 2. Register extensions
    extensionManager.registerExtensions([
      // Register OHIF extensions here
    ]);

    // 3. Initialize data source
    const dataSource = {
      // Configure DICOMweb data source
    };

    // 4. Load studies
    // 5. Setup viewport
    // 6. Apply hanging protocol
  };

  return (
    <div ref={viewerRef} className="ohif-viewer-container">
      {/* OHIF Viewer will be mounted here */}
    </div>
  );
};
```

**Challenges**:
- OHIF v3 has significantly changed architecture from v2
- May need to use `@ohif/app` package instead of building custom integration
- Extension system is complex and requires careful configuration
- Need to understand OHIF's new Mode-based architecture

**Alternative Approach (Recommended)**:
Instead of building custom integration, use OHIF as iframe or standalone app:

```typescript
export const OHIFViewer: React.FC<OHIFViewerProps> = ({ studyInstanceUIDs }) => {
  const viewerUrl = useMemo(() => {
    const studyUIDs = studyInstanceUIDs.join(',');
    return `/viewer?StudyInstanceUIDs=${studyUIDs}`;
  }, [studyInstanceUIDs]);

  return (
    <iframe
      src={viewerUrl}
      className="w-full h-screen border-0"
      title="OHIF Viewer"
    />
  );
};
```

This requires:
1. Running separate OHIF Viewer instance
2. Configuring OHIF to use our DICOMweb endpoints
3. Passing study UIDs via URL parameters

#### 2.2 Update OHIF Configuration

**File**: `app/frontend/src/config/ohif.config.ts`

Complete the configuration with:

```typescript
export default {
  routerBasename: '/viewer',

  // Data sources
  dataSources: [
    {
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'dicomweb',
      configuration: {
        name: 'MedAI DICOM Server',
        wadoUriRoot: `${API_BASE_URL}/api/dicom/dicom-web`,
        qidoRoot: `${API_BASE_URL}/api/dicom/dicom-web`,
        wadoRoot: `${API_BASE_URL}/api/dicom/dicom-web`,
        qidoSupportsIncludeField: true,
        imageRendering: 'wadors',
        thumbnailRendering: 'wadors',
        enableStudyLazyLoad: true,
        supportsFuzzyMatching: false,
        supportsWildcard: true,
        omitQuotationForMultipartRequest: true,
      },
    },
  ],

  // Default extensions
  extensions: [
    '@ohif/extension-default',
    '@ohif/extension-cornerstone',
    '@ohif/extension-measurement-tracking',
    '@ohif/extension-cornerstone-dicom-sr',
    '@ohif/extension-dicom-pdf',
  ],

  // Modes
  modes: [
    '@ohif/mode-longitudinal',
  ],

  // Customization
  showStudyList: true,
  maxNumberOfWebWorkers: 4,

  // Custom theme
  theme: {
    primaryColor: '#0ea5e9', // Medical blue
    backgroundColor: '#0f172a', // Dark slate
  },
};
```

#### 2.3 Update ToolsPage to Use Real Viewer

**File**: `app/frontend/src/pages/ToolsPage.tsx`

Replace:
```typescript
import OHIFViewerPlaceholder from '../components/viewer/OHIFViewerPlaceholder';
```

With:
```typescript
import OHIFViewer from '../components/viewer/OHIFViewer';
```

And update the conditional rendering:
```typescript
if (viewMode === 'viewer' && selectedStudyUID) {
  return (
    <OHIFViewer
      studyInstanceUIDs={[selectedStudyUID]}
      onClose={handleCloseViewer}
    />
  );
}
```

---

### Phase 3: Advanced Features (Medium Priority)

#### 3.1 Implement Image Caching

**Backend** - Add Redis caching for rendered frames:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# views.py
from django.core.cache import cache

def get_cached_frame(study_uid, series_uid, sop_uid, frame_number):
    cache_key = f"frame:{study_uid}:{series_uid}:{sop_uid}:{frame_number}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Render frame
    frame_data = render_dicom_frame(...)

    # Cache for 1 hour
    cache.set(cache_key, frame_data, 3600)
    return frame_data
```

**Docker** - Add Redis service:

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    container_name: redis-xrays
    ports:
      - "6379:6379"
    networks:
      - app-network
```

#### 3.2 Window/Level Presets

**Backend** - Implement preset management:

```python
# models.py
class WindowPreset(models.Model):
    name = models.CharField(max_length=100)
    modality = models.CharField(max_length=10)
    window_center = models.IntegerField()
    window_width = models.IntegerField()
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ['name', 'modality']

# Seed with common presets
PRESETS = [
    {'name': 'Lung', 'modality': 'CT', 'center': -600, 'width': 1500},
    {'name': 'Mediastinum', 'modality': 'CT', 'center': 50, 'width': 350},
    {'name': 'Bone', 'modality': 'CT', 'center': 300, 'width': 1500},
    {'name': 'Brain', 'modality': 'CT', 'center': 40, 'width': 80},
    {'name': 'Liver', 'modality': 'CT', 'center': 60, 'width': 160},
]
```

**Frontend** - Add preset selector to viewer:

```typescript
const windowPresets = {
  CT: [
    { name: 'Lung', center: -600, width: 1500 },
    { name: 'Mediastinum', center: 50, width: 350 },
    { name: 'Bone', center: 300, width: 1500 },
  ],
  // ... other modalities
};
```

#### 3.3 Hanging Protocols

**File**: `app/frontend/src/config/hangingProtocols.ts`

Define automatic layout rules:

```typescript
export const hangingProtocols = [
  {
    id: 'mpr',
    name: 'MPR',
    description: 'Multi-planar reconstruction',
    protocolMatchingRules: [
      {
        attribute: 'Modality',
        constraint: { equals: 'CT' },
      },
    ],
    displaySetSelectors: {
      // Configuration for which series to display
    },
    stages: [
      {
        name: 'MPR 2x2',
        viewportStructure: {
          type: 'grid',
          properties: {
            rows: 2,
            columns: 2,
          },
        },
        viewports: [
          { displaySetSelector: 'series1', viewportOptions: { orientation: 'axial' } },
          { displaySetSelector: 'series1', viewportOptions: { orientation: 'sagittal' } },
          { displaySetSelector: 'series1', viewportOptions: { orientation: 'coronal' } },
          { displaySetSelector: 'series1', viewportOptions: { orientation: '3d' } },
        ],
      },
    ],
  },
];
```

---

### Phase 4: AI Analysis Integration (Medium Priority)

#### 4.1 Create Analysis Results Model

**File**: `app/backend/dicom_images/models.py`

```python
class AnalysisResult(models.Model):
    """AI analysis results linked to medical images"""

    TYPE_CHOICES = [
        ('CLASSIFICATION', 'Classification'),
        ('SEGMENTATION', 'Segmentation'),
        ('DETECTION', 'Detection'),
        ('MEASUREMENT', 'Measurement'),
    ]

    image = models.ForeignKey(MedicalImage, on_delete=models.CASCADE, related_name='analyses')
    analysis_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    model_name = models.CharField(max_length=255)
    model_version = models.CharField(max_length=50)

    # Results
    predictions = models.JSONField(help_text="Prediction results as JSON")
    confidence_score = models.FloatField()

    # Segmentation mask (if applicable)
    segmentation_file = models.FileField(upload_to='analyses/segmentation/%Y/%m/%d/', null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    processing_time = models.FloatField(help_text="Processing time in seconds")

    class Meta:
        ordering = ['-created_at']
```

#### 4.2 Implement DICOM SEG Creation

**File**: `app/backend/dicom_images/utils.py`

```python
import numpy as np
from pydicom.dataset import Dataset
from pydicom.sr.codedict import codes

def create_dicom_seg(source_dcm, segmentation_mask, label_map):
    """
    Convert segmentation mask to DICOM Segmentation object

    Args:
        source_dcm: Source DICOM dataset
        segmentation_mask: numpy array with segmentation
        label_map: dict mapping label IDs to descriptions

    Returns:
        DICOM SEG dataset
    """
    seg = Dataset()

    # Copy patient/study info from source
    seg.PatientID = source_dcm.PatientID
    seg.StudyInstanceUID = source_dcm.StudyInstanceUID

    # Create new Series for segmentation
    seg.SeriesInstanceUID = generate_uid()
    seg.SOPClassUID = '1.2.840.10008.5.1.4.1.1.66.4'  # Segmentation Storage

    # Add segmentation data
    seg.SegmentSequence = create_segment_sequence(label_map)
    seg.PixelData = encode_segmentation(segmentation_mask)

    return seg
```

#### 4.3 Display Overlays in OHIF

**Frontend** - Configure OHIF to load segmentation overlays:

```typescript
// In OHIF config
const displaySetService = {
  makeDisplaySet: (instances) => {
    // Check if instance is segmentation
    if (instance.SOPClassUID === '1.2.840.10008.5.1.4.1.1.66.4') {
      return {
        displaySetInstanceUID: generateId(),
        SeriesDescription: 'AI Segmentation',
        Modality: 'SEG',
        isOverlay: true,
        // ... other properties
      };
    }
  },
};
```

---

### Phase 5: Testing & Optimization (High Priority)

#### 5.1 Create Test DICOM Datasets

**Directory**: `app/backend/fixtures/test_dicom/`

Include:
- Single-frame CT chest image
- Multi-frame cardiac CT
- MRI brain series (10-20 slices)
- Ultrasound cine loop
- X-ray with various modalities
- Sample segmentation DICOM SEG
- Sample structured report DICOM SR

Sources:
- TCIA (The Cancer Imaging Archive)
- DICOM Sample Files repository
- Create synthetic test data

#### 5.2 Unit Tests

**File**: `app/backend/dicom_images/tests.py`

```python
from django.test import TestCase
from rest_framework.test import APIClient
import pydicom

class DicomUploadTestCase(TestCase):
    def test_upload_valid_dicom(self):
        """Test uploading a valid DICOM file"""

    def test_upload_invalid_file(self):
        """Test uploading non-DICOM file returns error"""

    def test_metadata_extraction(self):
        """Test DICOM metadata is correctly extracted"""

    def test_storage_quota_enforcement(self):
        """Test upload fails when quota exceeded"""

class WADORSTestCase(TestCase):
    def test_retrieve_instance(self):
        """Test WADO-RS instance retrieval"""

    def test_retrieve_frame_jpeg(self):
        """Test frame retrieval as JPEG"""

    def test_windowing_application(self):
        """Test window/level adjustment"""
```

#### 5.3 Integration Tests

**File**: `app/frontend/src/__tests__/OHIFIntegration.test.tsx`

```typescript
describe('OHIF Viewer Integration', () => {
  it('loads study in viewer', async () => {
    // Test study loading
  });

  it('displays series in viewport', async () => {
    // Test series display
  });

  it('applies window/level preset', async () => {
    // Test windowing
  });

  it('loads segmentation overlay', async () => {
    // Test overlay display
  });
});
```

#### 5.4 Performance Testing

Areas to test:
- Frame retrieval latency (target: <100ms)
- Concurrent user handling (target: 50+ simultaneous viewers)
- Large study loading (100+ images)
- Memory usage during extended viewing sessions
- Network bandwidth for high-resolution images

Tools:
- Apache JMeter for load testing
- Chrome DevTools Performance profiler
- Django Debug Toolbar

---

## Technical Considerations

### Security

1. **Authentication for WADO-RS**
   - Ensure all image retrieval endpoints check authentication
   - Consider using token-based auth for OHIF requests
   - Implement rate limiting on frame retrieval

2. **PHI Protection**
   - Sanitize DICOM tags before sending to frontend
   - Remove/anonymize sensitive metadata fields
   - Audit log all image access

3. **CORS Configuration**
   - Lock down CORS to specific origins in production
   - Use proper credentials handling

### Performance

1. **Image Compression**
   - Use JPEG with quality=90 for lossy compression
   - Consider JPEG 2000 for better compression ratios
   - Implement progressive JPEG loading

2. **Caching Strategy**
   - Browser cache headers for immutable resources
   - Redis cache for frequently accessed frames
   - CDN for static OHIF assets

3. **Lazy Loading**
   - Load only visible frames initially
   - Prefetch adjacent frames
   - Unload frames from memory when not visible

### Compatibility

1. **DICOM Transfer Syntaxes**
   - Support common compressed syntaxes (JPEG, JPEG 2000, RLE)
   - Handle implicit/explicit VR
   - Gracefully handle unsupported syntaxes

2. **Browser Support**
   - Test on Chrome, Firefox, Safari, Edge
   - Ensure WebGL support for 3D rendering
   - Fallback for older browsers

---

## Success Criteria

### Must Have (MVP)
- [ ] Users can view DICOM images in OHIF Viewer
- [ ] Basic window/level adjustment works
- [ ] Multi-series studies display correctly
- [ ] Measurement tools (length, angle) function
- [ ] Study navigation (next/previous image) works
- [ ] Performance: <100ms frame load time

### Should Have
- [ ] Window/level presets for CT, MR modalities
- [ ] Thumbnail strip for quick navigation
- [ ] Cine mode for multi-frame images
- [ ] Zoom, pan, rotate tools work
- [ ] Annotations persist across sessions
- [ ] Export measurements to report

### Nice to Have
- [ ] MPR (multi-planar reconstruction) for 3D datasets
- [ ] Volume rendering for CT/MRI
- [ ] Hanging protocols auto-apply
- [ ] AI segmentation overlays display
- [ ] Comparison mode for before/after studies
- [ ] DICOM SR rendering

---

## Migration Path from Placeholder

### Step-by-Step Replacement

1. **Keep Placeholder in Parallel**
   ```typescript
   // ToolsPage.tsx
   const [useRealViewer, setUseRealViewer] = useState(false);

   {viewMode === 'viewer' && selectedStudyUID && (
     useRealViewer ? (
       <OHIFViewer studyInstanceUIDs={[selectedStudyUID]} onClose={...} />
     ) : (
       <OHIFViewerPlaceholder studyUID={selectedStudyUID} onClose={...} />
     )
   )}
   ```

2. **Add Feature Flag**
   ```typescript
   // Feature flag in environment or user preferences
   const ENABLE_OHIF_VIEWER = import.meta.env.VITE_ENABLE_OHIF === 'true';
   ```

3. **Gradual Rollout**
   - Enable for admin users first
   - Collect feedback and fix issues
   - Enable for all users
   - Remove placeholder code

---

## Resource Requirements

### Development
- **Backend Developer**: Implement WADO-RS endpoints, image processing
- **Frontend Developer**: OHIF integration, React components
- **DevOps**: Redis setup, performance optimization
- **QA**: Test with various DICOM files, cross-browser testing

### Infrastructure
- **Redis**: For image caching (Docker container)
- **Additional Storage**: Expect 2-3x storage for cached images
- **CPU**: Image processing is CPU-intensive, consider worker processes
- **Memory**: DICOM parsing can be memory-intensive (2-4GB recommended)

### Timeline Estimate
- **Phase 1 (WADO-RS)**: Implement backend endpoints
- **Phase 2 (OHIF)**: Integrate OHIF Viewer
- **Phase 3 (Features)**: Add advanced features
- **Phase 4 (AI)**: Integrate AI analysis
- **Phase 5 (Testing)**: Comprehensive testing

---

## Known Issues & Risks

### OHIF v3 Complexity
**Issue**: OHIF v3 has significantly different architecture from v2
**Risk**: High learning curve, potential for integration issues
**Mitigation**: Consider using OHIF Standalone mode with iframe integration initially

### Image Processing Performance
**Issue**: Real-time DICOM-to-JPEG conversion is CPU-intensive
**Risk**: Slow frame loading, poor user experience
**Mitigation**: Implement aggressive caching, consider pre-rendering on upload

### Browser Memory Limits
**Issue**: Large studies (500+ images) can exhaust browser memory
**Risk**: Browser crashes, slow performance
**Mitigation**: Implement progressive loading, unload off-screen frames

### DICOM Codec Support
**Issue**: Some DICOM files use proprietary compression
**Risk**: Unable to display certain images
**Mitigation**: Use GDCM library for broader codec support, provide clear error messages

---

## References

### Documentation
- [OHIF Viewer Documentation](https://docs.ohif.org/)
- [DICOMweb Standard](https://www.dicomstandard.org/using/dicomweb)
- [Pydicom Documentation](https://pydicom.github.io/)
- [Cornerstone Documentation](https://cornerstonejs.org/)

### Example Implementations
- [OHIF Platform Repository](https://github.com/OHIF/Viewers)
- [DICOMweb Server Examples](https://github.com/dcmjs-org/dicomweb-server)
- [Django DICOM](https://github.com/openmedlab/django-dicom)

### Test Data
- [TCIA Collections](https://www.cancerimagingarchive.net/)
- [DICOM Sample Files](https://www.rubomedical.com/dicom_files/)
- [Medical Image Datasets](https://github.com/sfikas/medical-imaging-datasets)

---

## Next Immediate Steps

1. **Review this plan** with team/stakeholders
2. **Set up development environment** for WADO-RS testing
3. **Download test DICOM files** to `fixtures/` directory
4. **Implement basic WADO-RS frame retrieval** endpoint
5. **Test frame rendering** with curl/Postman
6. **Create simple OHIF integration** proof-of-concept
7. **Iterate based on findings**

---

## Questions for Stakeholders

1. **Priority**: Is full OHIF integration required immediately, or can we iterate?
2. **Scope**: Which OHIF features are must-have vs. nice-to-have?
3. **Performance**: What are acceptable frame load times?
4. **Storage**: What are constraints on image caching storage?
5. **AI Integration**: Should analysis overlays be prioritized?
6. **Deployment**: Will OHIF run embedded or as separate service?

---

**Document Version**: 1.0
**Last Updated**: 2025-12-20
**Author**: Claude (AI Assistant)
**Status**: Ready for Review
