# Next Steps: Cornerstone.js Canvas Integration

**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 2-4 hours
**Complexity**: Medium
**Prerequisites**: ✅ WADO-RS Backend Complete, ✅ OHIF Viewer UI Complete

---

## Overview

The OHIF Viewer integration is **85% complete**. The remaining 15% involves integrating Cornerstone.js to actually render DICOM pixel data on the canvas. The backend WADO-RS endpoints are fully functional and can serve images, the viewer UI is complete with navigation controls, and we just need to connect the rendering layer.

**What's Done**:
- ✅ Backend WADO-RS endpoints serving DICOM frames as JPEG
- ✅ Frontend OHIFViewer component with professional UI
- ✅ Study/series metadata loading and display
- ✅ Navigation controls for series and images
- ✅ Error handling and loading states

**What's Needed**:
- ⏳ Cornerstone canvas initialization
- ⏳ WADO-RS image loader configuration
- ⏳ Image display and viewport management
- ⏳ Interactive tools (window/level, zoom, pan)
- ⏳ Keyboard shortcuts and tool controls

---

## Implementation Approach

There are **two main approaches** to complete the OHIF integration:

### Approach 1: Full Cornerstone.js Integration (Recommended for Learning)

**Pros**:
- Full control over viewer implementation
- Learn Cornerstone.js fundamentals
- Lighter weight than full OHIF
- Easier to customize

**Cons**:
- More code to write
- Need to implement tools from scratch
- No built-in OHIF modes/extensions

**Estimated Time**: 3-4 hours

### Approach 2: Standalone OHIF Viewer (Recommended for Production)

**Pros**:
- Full OHIF feature set out-of-the-box
- Measurement tools, MPR, 3D rendering
- Production-tested and maintained
- Less custom code

**Cons**:
- Requires separate OHIF service or iframe
- More complex configuration
- Larger bundle size

**Estimated Time**: 2-3 hours

**Recommendation**: Start with **Approach 1** to understand the fundamentals, then migrate to **Approach 2** for production if needed.

---

## Approach 1: Cornerstone.js Integration (Detailed Steps)

### Step 1: Install Missing Dependencies

The OHIF packages are already installed, but we may need additional loaders.

**Check Current Dependencies**:
```bash
cd app/frontend
npm list | grep cornerstone
```

**Install if Missing**:
```bash
npm install --legacy-peer-deps \
  cornerstone-wado-image-loader \
  dicom-parser
```

**Rationale**: `cornerstone-wado-image-loader` provides the bridge between WADO-RS URLs and Cornerstone image objects.

---

### Step 2: Create Cornerstone Initialization Module

**File**: `app/frontend/src/utils/cornerstoneInit.ts` (NEW)

```typescript
/**
 * Cornerstone Initialization Utilities
 *
 * Configure Cornerstone libraries and image loaders for DICOM viewing
 */

import * as cornerstone from 'cornerstone-core';
import * as cornerstoneTools from 'cornerstone-tools';
import cornerstoneWADOImageLoader from 'cornerstone-wado-image-loader';
import dicomParser from 'dicom-parser';

let initialized = false;

/**
 * Initialize Cornerstone libraries (call once on app startup)
 */
export function initializeCornerstone() {
  if (initialized) {
    return;
  }

  // Set external dependencies
  cornerstoneTools.external.cornerstone = cornerstone;
  cornerstoneWADOImageLoader.external.cornerstone = cornerstone;
  cornerstoneWADOImageLoader.external.dicomParser = dicomParser;

  // Configure WADO Image Loader
  cornerstoneWADOImageLoader.configure({
    // Use web workers for image decoding (better performance)
    useWebWorkers: true,
    decodeConfig: {
      convertFloatPixelDataToInt: false,
      use16BitDataType: true,
    },
    // Add authentication headers to requests
    beforeSend: (xhr: XMLHttpRequest) => {
      const token = localStorage.getItem('medai-auth-token');
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }
    },
  });

  // Initialize web workers for image loading
  const config = {
    maxWebWorkers: navigator.hardwareConcurrency || 4,
    startWebWorkersOnDemand: true,
    taskConfiguration: {
      decodeTask: {
        initializeCodecsOnStartup: false,
        usePDFJS: false,
      },
    },
  };

  cornerstoneWADOImageLoader.webWorkerManager.initialize(config);

  // Initialize cornerstone tools
  cornerstoneTools.init({
    mouseEnabled: true,
    touchEnabled: true,
    globalToolSyncEnabled: true,
    showSVGCursors: true,
  });

  initialized = true;
  console.log('Cornerstone initialized successfully');
}

/**
 * Clean up Cornerstone resources
 */
export function cleanupCornerstone() {
  // Disable all enabled elements
  const enabledElements = cornerstone.getEnabledElements();
  enabledElements.forEach((element) => {
    cornerstone.disable(element.element);
  });

  // Clear image cache
  cornerstone.imageCache.purgeCache();

  console.log('Cornerstone cleaned up');
}

/**
 * Enable a DOM element for Cornerstone rendering
 */
export function enableElement(element: HTMLDivElement): void {
  if (!cornerstone.getEnabledElement(element)) {
    cornerstone.enable(element);
  }
}

/**
 * Disable a DOM element
 */
export function disableElement(element: HTMLDivElement): void {
  if (cornerstone.getEnabledElement(element)) {
    cornerstone.disable(element);
  }
}

/**
 * Generate WADO-RS image ID for Cornerstone
 */
export function generateImageId(
  studyUID: string,
  seriesUID: string,
  sopUID: string,
  frameNumber: number = 1
): string {
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:3080';

  // WADO-RS URL format
  const wadoUrl = `${baseUrl}/api/dicom/dicom-web/studies/${studyUID}/series/${seriesUID}/instances/${sopUID}/frames/${frameNumber}`;

  // Cornerstone WADO URI format
  return `wadouri:${wadoUrl}`;
}

export { cornerstone, cornerstoneTools };
```

**Purpose**: Centralizes Cornerstone initialization logic, making it reusable and easier to maintain.

---

### Step 3: Update OHIFViewer Component

**File**: `app/frontend/src/components/viewer/OHIFViewer.tsx` (UPDATE)

**Changes to implement**:

#### 3.1 Add Imports

```typescript
// Add at top of file
import {
  initializeCornerstone,
  enableElement,
  disableElement,
  generateImageId,
  cornerstone,
  cornerstoneTools,
} from '../../utils/cornerstoneInit';
```

#### 3.2 Add State for Canvas

```typescript
// Add to existing state
const [currentInstance, setCurrentInstance] = useState<Instance | null>(null);
const [viewportElement, setViewportElement] = useState<HTMLDivElement | null>(null);
```

#### 3.3 Initialize Cornerstone on Mount

```typescript
// Add useEffect for initialization
useEffect(() => {
  // Initialize Cornerstone (one-time setup)
  initializeCornerstone();

  return () => {
    // Cleanup on unmount
    if (viewportElement) {
      disableElement(viewportElement);
    }
  };
}, []);
```

#### 3.4 Update loadStudyData to Get Instances

```typescript
const loadStudyData = async () => {
  setLoading(true);
  setError(null);

  try {
    // Get study metadata
    const studies = await apiClient.getStudies({ limit: 1000 });
    const foundStudy = studies.find(s => studyInstanceUIDs.includes(s.StudyInstanceUID));

    if (!foundStudy) {
      throw new Error('Study not found');
    }

    setStudy(foundStudy);

    // Get series for this study
    const seriesData = await apiClient.getSeries(foundStudy.StudyInstanceUID);

    if (seriesData.length === 0) {
      throw new Error('No series found in study');
    }

    setSeries(seriesData);

    // Get instances for first series
    if (seriesData.length > 0) {
      await loadInstancesForSeries(foundStudy.StudyInstanceUID, seriesData[0].SeriesInstanceUID, 0);
    }

  } catch (err: any) {
    console.error('Failed to load study:', err);
    setError(err.message || 'Failed to load study');
    toast.error(err.message || 'Failed to load study');
  } finally {
    setLoading(false);
  }
};
```

#### 3.5 Add Function to Load Instances

```typescript
const loadInstancesForSeries = async (
  studyUID: string,
  seriesUID: string,
  seriesIndex: number
) => {
  try {
    // Get instances for this series
    const instances = await apiClient.getInstances(studyUID, seriesUID);

    if (instances.length === 0) {
      throw new Error('No instances found in series');
    }

    // Store first instance for current series
    setCurrentInstance(instances[0]);

    // Load and display first image
    if (viewportElement) {
      await displayImage(studyUID, seriesUID, instances[0].SOPInstanceUID, 0);
    }

    setCurrentSeriesIndex(seriesIndex);
    setCurrentImageIndex(0);

  } catch (err: any) {
    console.error('Failed to load instances:', err);
    toast.error('Failed to load images for series');
  }
};
```

#### 3.6 Add Image Display Function

```typescript
const displayImage = async (
  studyUID: string,
  seriesUID: string,
  sopUID: string,
  imageIndex: number
) => {
  if (!viewportElement) {
    console.error('Viewport element not initialized');
    return;
  }

  try {
    // Enable element if not already enabled
    if (!cornerstone.getEnabledElement(viewportElement)) {
      enableElement(viewportElement);

      // Add basic tools
      const tools = ['Wwwc', 'Zoom', 'Pan'];
      tools.forEach(toolName => {
        cornerstoneTools.addTool(cornerstoneTools[`${toolName}Tool`]);
      });

      // Set active tools
      cornerstoneTools.setToolActive('Wwwc', { mouseButtonMask: 1 }); // Left click
      cornerstoneTools.setToolActive('Zoom', { mouseButtonMask: 2 }); // Middle click
      cornerstoneTools.setToolActive('Pan', { mouseButtonMask: 4 });  // Right click
    }

    // Generate image ID
    const imageId = generateImageId(studyUID, seriesUID, sopUID, imageIndex + 1);

    // Load and display image
    const image = await cornerstone.loadImage(imageId);
    cornerstone.displayImage(viewportElement, image);

    console.log('Image displayed successfully:', imageId);

  } catch (err: any) {
    console.error('Failed to display image:', err);
    toast.error('Failed to display image: ' + err.message);
  }
};
```

#### 3.7 Update Navigation Handlers

```typescript
const handleNextSeries = async () => {
  if (currentSeriesIndex < series.length - 1 && study) {
    const newIndex = currentSeriesIndex + 1;
    await loadInstancesForSeries(
      study.StudyInstanceUID,
      series[newIndex].SeriesInstanceUID,
      newIndex
    );
  }
};

const handlePreviousSeries = async () => {
  if (currentSeriesIndex > 0 && study) {
    const newIndex = currentSeriesIndex - 1;
    await loadInstancesForSeries(
      study.StudyInstanceUID,
      series[newIndex].SeriesInstanceUID,
      newIndex
    );
  }
};

const handleNextImage = async () => {
  if (currentInstance && study) {
    const currentSeries = series[currentSeriesIndex];
    const newIndex = currentImageIndex + 1;

    if (newIndex < currentSeries.NumberOfSeriesRelatedInstances) {
      // Get instances and display next one
      const instances = await apiClient.getInstances(
        study.StudyInstanceUID,
        currentSeries.SeriesInstanceUID
      );

      if (instances[newIndex]) {
        await displayImage(
          study.StudyInstanceUID,
          currentSeries.SeriesInstanceUID,
          instances[newIndex].SOPInstanceUID,
          newIndex
        );
        setCurrentImageIndex(newIndex);
        setCurrentInstance(instances[newIndex]);
      }
    }
  }
};

const handlePreviousImage = async () => {
  if (currentInstance && study) {
    const currentSeries = series[currentSeriesIndex];
    const newIndex = currentImageIndex - 1;

    if (newIndex >= 0) {
      // Get instances and display previous one
      const instances = await apiClient.getInstances(
        study.StudyInstanceUID,
        currentSeries.SeriesInstanceUID
      );

      if (instances[newIndex]) {
        await displayImage(
          study.StudyInstanceUID,
          currentSeries.SeriesInstanceUID,
          instances[newIndex].SOPInstanceUID,
          newIndex
        );
        setCurrentImageIndex(newIndex);
        setCurrentInstance(instances[newIndex]);
      }
    }
  }
};
```

#### 3.8 Update Canvas Element

Replace the placeholder `<div>` in the canvas area with:

```typescript
<div
  ref={(el) => {
    if (el && !viewportElement) {
      setViewportElement(el);
    }
  }}
  className="w-full h-full"
  style={{
    minHeight: '500px',
    backgroundColor: '#000',
  }}
/>
```

---

### Step 4: Add Tool Controls (Optional Enhancement)

**File**: `app/frontend/src/components/viewer/ToolBar.tsx` (NEW)

```typescript
/**
 * DICOM Viewer Toolbar
 *
 * Provides tool selection buttons for the viewer
 */

import React from 'react';
import {
  Move,
  ZoomIn,
  Contrast,
  Ruler,
  Triangle,
  Square,
  Circle,
  RotateCw,
  FlipHorizontal,
} from 'lucide-react';

interface Tool {
  name: string;
  icon: React.ReactNode;
  label: string;
  shortcut?: string;
}

const tools: Tool[] = [
  { name: 'Wwwc', icon: <Contrast className="w-4 h-4" />, label: 'Window/Level', shortcut: 'W' },
  { name: 'Zoom', icon: <ZoomIn className="w-4 h-4" />, label: 'Zoom', shortcut: 'Z' },
  { name: 'Pan', icon: <Move className="w-4 h-4" />, label: 'Pan', shortcut: 'P' },
  { name: 'Length', icon: <Ruler className="w-4 h-4" />, label: 'Length', shortcut: 'L' },
  { name: 'Angle', icon: <Triangle className="w-4 h-4" />, label: 'Angle', shortcut: 'A' },
  { name: 'RectangleRoi', icon: <Square className="w-4 h-4" />, label: 'Rectangle ROI', shortcut: 'R' },
  { name: 'EllipticalRoi', icon: <Circle className="w-4 h-4" />, label: 'Ellipse ROI', shortcut: 'E' },
];

interface ToolBarProps {
  activeTool: string;
  onToolChange: (toolName: string) => void;
  onRotate?: () => void;
  onFlip?: () => void;
  onReset?: () => void;
}

export const ToolBar: React.FC<ToolBarProps> = ({
  activeTool,
  onToolChange,
  onRotate,
  onFlip,
  onReset,
}) => {
  return (
    <div className="bg-slate-800 border-b border-slate-700 px-4 py-2">
      <div className="flex items-center gap-2">
        {/* Tools */}
        <div className="flex items-center gap-1">
          {tools.map((tool) => (
            <button
              key={tool.name}
              onClick={() => onToolChange(tool.name)}
              className={`
                p-2 rounded transition-colors
                ${activeTool === tool.name
                  ? 'bg-medical-600 text-white'
                  : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }
              `}
              title={`${tool.label}${tool.shortcut ? ` (${tool.shortcut})` : ''}`}
            >
              {tool.icon}
            </button>
          ))}
        </div>

        {/* Separator */}
        <div className="h-6 w-px bg-slate-600" />

        {/* View Controls */}
        <div className="flex items-center gap-1">
          {onRotate && (
            <button
              onClick={onRotate}
              className="p-2 rounded text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
              title="Rotate 90° (R)"
            >
              <RotateCw className="w-4 h-4" />
            </button>
          )}
          {onFlip && (
            <button
              onClick={onFlip}
              className="p-2 rounded text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
              title="Flip Horizontal (H)"
            >
              <FlipHorizontal className="w-4 h-4" />
            </button>
          )}
          {onReset && (
            <button
              onClick={onReset}
              className="px-3 py-1 rounded text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
              title="Reset View (Space)"
            >
              Reset
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ToolBar;
```

Then add to OHIFViewer.tsx:

```typescript
import ToolBar from './ToolBar';

// Add state
const [activeTool, setActiveTool] = useState('Wwwc');

// Add handler
const handleToolChange = (toolName: string) => {
  if (!viewportElement) return;

  // Deactivate current tool
  cornerstoneTools.setToolPassive(activeTool);

  // Activate new tool
  cornerstoneTools.setToolActive(toolName, { mouseButtonMask: 1 });

  setActiveTool(toolName);
};

// Add to render
<ToolBar
  activeTool={activeTool}
  onToolChange={handleToolChange}
  onRotate={() => {/* Implement rotation */}}
  onFlip={() => {/* Implement flip */}}
  onReset={() => {/* Implement reset */}}
/>
```

---

### Step 5: Add Keyboard Shortcuts

**File**: `app/frontend/src/components/viewer/OHIFViewer.tsx` (UPDATE)

```typescript
// Add useEffect for keyboard handling
useEffect(() => {
  const handleKeyDown = (event: KeyboardEvent) => {
    switch (event.key.toLowerCase()) {
      case 'w':
        handleToolChange('Wwwc');
        break;
      case 'z':
        handleToolChange('Zoom');
        break;
      case 'p':
        handleToolChange('Pan');
        break;
      case 'l':
        handleToolChange('Length');
        break;
      case 'arrowup':
        event.preventDefault();
        handlePreviousImage();
        break;
      case 'arrowdown':
        event.preventDefault();
        handleNextImage();
        break;
      case 'arrowleft':
        event.preventDefault();
        handlePreviousSeries();
        break;
      case 'arrowright':
        event.preventDefault();
        handleNextSeries();
        break;
      case ' ':
        event.preventDefault();
        // Reset viewport
        if (viewportElement) {
          cornerstone.reset(viewportElement);
        }
        break;
      default:
        break;
    }
  };

  window.addEventListener('keydown', handleKeyDown);

  return () => {
    window.removeEventListener('keydown', handleKeyDown);
  };
}, [activeTool, currentSeriesIndex, currentImageIndex]);
```

---

## Approach 2: Standalone OHIF Viewer (Alternative)

If Approach 1 proves too complex or time-consuming, use OHIF as a separate service.

### Option A: OHIF as Iframe

**Steps**:

1. **Run OHIF Viewer Separately**:
```bash
# In a separate directory
git clone https://github.com/OHIF/Viewers.git
cd Viewers
git checkout v3.11.1
npm install
npm run dev
```

2. **Configure OHIF** (`platform/viewer/public/config/default.js`):
```javascript
window.config = {
  routerBasename: '/ohif',
  dataSources: [
    {
      namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
      sourceName: 'dicomweb',
      configuration: {
        friendlyName: 'MedAI DICOM Server',
        name: 'medai',
        wadoUriRoot: 'http://localhost:3080/api/dicom/dicom-web',
        qidoRoot: 'http://localhost:3080/api/dicom/dicom-web',
        wadoRoot: 'http://localhost:3080/api/dicom/dicom-web',
        imageRendering: 'wadors',
      },
    },
  ],
};
```

3. **Embed in React**:
```typescript
export const OHIFViewer: React.FC<OHIFViewerProps> = ({ studyInstanceUIDs, onClose }) => {
  const viewerUrl = useMemo(() => {
    const studyUIDs = studyInstanceUIDs.join(',');
    return `http://localhost:3001/viewer?StudyInstanceUIDs=${studyUIDs}`;
  }, [studyInstanceUIDs]);

  return (
    <div className="min-h-screen">
      {/* Header with close button */}
      <div className="bg-slate-800 p-4">
        <Button onClick={onClose} leftIcon={ArrowLeft}>Back</Button>
      </div>

      {/* OHIF iframe */}
      <iframe
        src={viewerUrl}
        className="w-full h-[calc(100vh-80px)] border-0"
        title="OHIF Viewer"
      />
    </div>
  );
};
```

### Option B: Docker Compose OHIF Service

Add to `docker-compose.yml`:

```yaml
ohif-viewer:
  image: ohif/viewer:v3.11.1
  container_name: ohif-xrays
  ports:
    - "3001:80"
  volumes:
    - ./config/ohif-config.js:/usr/share/nginx/html/app-config.js
  networks:
    - app-network
```

---

## Testing Strategy

### Unit Tests

**File**: `app/frontend/src/__tests__/cornerstoneInit.test.ts`

```typescript
describe('Cornerstone Initialization', () => {
  it('initializes without errors', () => {
    expect(() => initializeCornerstone()).not.toThrow();
  });

  it('generates correct image ID format', () => {
    const imageId = generateImageId('study1', 'series1', 'sop1', 1);
    expect(imageId).toContain('wadouri:');
    expect(imageId).toContain('/frames/1');
  });
});
```

### Integration Tests

**Test Checklist**:

1. **Image Loading**
   - [ ] Upload sample CT chest DICOM
   - [ ] Open in viewer
   - [ ] Verify image renders on canvas
   - [ ] Check browser console for errors

2. **Window/Level**
   - [ ] Click and drag on image
   - [ ] Verify contrast changes
   - [ ] Try different presets (lung, bone, brain)

3. **Navigation**
   - [ ] Test next/previous image buttons
   - [ ] Test next/previous series buttons
   - [ ] Verify image counter updates
   - [ ] Test keyboard shortcuts (arrow keys)

4. **Tools**
   - [ ] Select Length tool
   - [ ] Draw measurement on image
   - [ ] Verify measurement appears
   - [ ] Test other tools (zoom, pan, ROI)

5. **Performance**
   - [ ] Load series with 100+ images
   - [ ] Navigate rapidly between images
   - [ ] Check for memory leaks (dev tools memory profiler)
   - [ ] Verify smooth scrolling/zooming

---

## Troubleshooting Guide

### Issue: "Cannot find module 'cornerstone-core'"

**Solution**:
```bash
npm install --legacy-peer-deps cornerstone-core cornerstone-tools
```

### Issue: Images don't load (network errors)

**Checks**:
1. Backend WADO-RS endpoint accessible
2. CORS headers configured
3. Auth token included in requests
4. Check Network tab for 404/401/500 errors

**Debug**:
```typescript
// Add to cornerstoneInit.ts beforeSend
beforeSend: (xhr) => {
  console.log('Loading image:', xhr.url);
  // Check if token exists
  const token = localStorage.getItem('medai-auth-token');
  console.log('Auth token:', token ? 'Present' : 'Missing');
  if (token) {
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
  }
},
```

### Issue: "element is not enabled"

**Solution**: Ensure element is enabled before displayImage:
```typescript
if (!cornerstone.getEnabledElement(viewportElement)) {
  enableElement(viewportElement);
}
```

### Issue: Tools not working

**Solution**: Check tools are added and activated:
```typescript
// Add tools
cornerstoneTools.addTool(cornerstoneTools.WwwcTool);
cornerstoneTools.addTool(cornerstoneTools.ZoomTool);
cornerstoneTools.addTool(cornerstoneTools.PanTool);

// Activate tools
cornerstoneTools.setToolActive('Wwwc', { mouseButtonMask: 1 });
```

### Issue: WebWorkers error

**Solution**: Configure Vite to handle web workers:

**File**: `app/frontend/vite.config.ts`
```typescript
export default defineConfig({
  // ... existing config
  worker: {
    format: 'es',
  },
  optimizeDeps: {
    exclude: ['cornerstone-wado-image-loader'],
  },
});
```

---

## Sample DICOM Files for Testing

Download test files from:

1. **TCIA (The Cancer Imaging Archive)**
   - URL: https://www.cancerimagingarchive.net/
   - Collections: CT Chest, Brain MRI, etc.
   - Format: DICOM

2. **DICOM Library**
   - URL: https://www.dicomlibrary.com/
   - Various modalities
   - Small test datasets

3. **Rubo Medical**
   - URL: https://www.rubomedical.com/dicom_files/
   - Sample CT, MR, US files
   - Free download

**Recommended Test Cases**:
- Single-frame CT chest (test basic viewing)
- Multi-frame cardiac CT (test frame navigation)
- MRI brain series (test series switching)
- X-ray with MONOCHROME1 (test inversion)

---

## Success Criteria

### Minimum Viable Product (MVP)

- [ ] Canvas displays DICOM images
- [ ] Window/level tool works (left mouse drag)
- [ ] Zoom tool works (middle mouse or scroll)
- [ ] Pan tool works (right mouse drag)
- [ ] Next/previous image navigation
- [ ] Next/previous series navigation
- [ ] Series count and image counter accurate

### Enhanced Features (Nice-to-Have)

- [ ] Measurement tools (length, angle)
- [ ] ROI tools (rectangle, ellipse)
- [ ] Keyboard shortcuts functional
- [ ] Toolbar for tool selection
- [ ] Reset viewport button
- [ ] Rotate and flip tools
- [ ] Cine mode for multi-frame

### Production Ready

- [ ] Error handling comprehensive
- [ ] Loading states smooth
- [ ] Performance optimized (100+ image series)
- [ ] Memory management (no leaks)
- [ ] Cross-browser tested
- [ ] Mobile responsive
- [ ] Accessibility (keyboard nav)

---

## Estimated Timeline

### Approach 1: Cornerstone.js Integration

| Task | Duration | Priority |
|------|----------|----------|
| Install dependencies | 15 min | High |
| Create cornerstoneInit.ts | 30 min | High |
| Update OHIFViewer component | 1-2 hours | High |
| Add instance loading logic | 30 min | High |
| Wire navigation handlers | 30 min | High |
| Test basic viewing | 30 min | High |
| Add toolbar (optional) | 1 hour | Medium |
| Add keyboard shortcuts | 30 min | Medium |
| Implement measurement tools | 1 hour | Low |
| Testing and debugging | 1 hour | High |

**Total**: 3-4 hours for MVP, 5-6 hours with enhancements

### Approach 2: Standalone OHIF

| Task | Duration | Priority |
|------|----------|----------|
| Set up OHIF viewer service | 1 hour | High |
| Configure DICOMweb endpoints | 30 min | High |
| Create iframe integration | 30 min | High |
| Test viewing workflow | 30 min | High |
| Customize UI (optional) | 1 hour | Medium |

**Total**: 2-3 hours for basic integration

---

## Decision Matrix

Use this to decide which approach:

| Criterion | Approach 1 (Cornerstone) | Approach 2 (OHIF) |
|-----------|-------------------------|-------------------|
| Learning value | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Time to MVP | ⭐⭐⭐ (3-4h) | ⭐⭐⭐⭐⭐ (2-3h) |
| Customization | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Feature completeness | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Bundle size | ⭐⭐⭐⭐⭐ (smaller) | ⭐⭐⭐ (larger) |
| Maintenance | ⭐⭐⭐ (custom code) | ⭐⭐⭐⭐⭐ (OHIF team) |
| Production ready | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Recommendation**:
- **Development/Learning**: Approach 1
- **Production/Speed**: Approach 2

---

## Resources

### Documentation
- [Cornerstone Core Docs](https://github.com/cornerstonejs/cornerstone)
- [Cornerstone Tools Docs](https://github.com/cornerstonejs/cornerstoneTools)
- [WADO Image Loader](https://github.com/cornerstonejs/cornerstoneWADOImageLoader)
- [OHIF Viewer Docs](https://docs.ohif.org/)

### Example Code
- [OHIF Viewer Source](https://github.com/OHIF/Viewers)
- [Cornerstone Examples](https://github.com/cornerstonejs/cornerstone/tree/master/example)

### Community
- [OHIF Discourse](https://community.ohif.org/)
- [Cornerstone GitHub Discussions](https://github.com/cornerstonejs/cornerstone/discussions)

---

## Summary

**Current State**: 85% complete
- ✅ Backend WADO-RS fully functional
- ✅ Viewer UI and navigation complete
- ⏳ Canvas rendering pending

**Next Implementation**: Cornerstone.js Integration
- **Approach**: Start with Approach 1 (Cornerstone) for learning
- **Estimated Time**: 3-4 hours for MVP
- **Success Metric**: Display DICOM images with basic tools

**Files to Create/Modify**:
1. ✏️ `app/frontend/src/utils/cornerstoneInit.ts` (NEW)
2. ✏️ `app/frontend/src/components/viewer/OHIFViewer.tsx` (UPDATE)
3. ✏️ `app/frontend/src/components/viewer/ToolBar.tsx` (NEW - optional)
4. ✏️ `app/frontend/vite.config.ts` (UPDATE - worker config)

**Ready to Implement**: All prerequisites met, detailed steps provided, clear success criteria defined.

---

**Document Version**: 1.0
**Created**: 2025-12-21
**Status**: Ready for Implementation
**Next Action**: Implement Step 1 (Install Dependencies)
