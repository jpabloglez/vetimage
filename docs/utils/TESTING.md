# DICOM Viewer Testing Guide

**Created**: 2025-12-21
**Purpose**: Step-by-step testing instructions for the Cornerstone DICOM viewer
**Status**: Ready for Testing

---

## Prerequisites

### 1. Services Running

Verify all services are running:

```bash
docker ps
```

You should see:
- `frontend-xrays` - Running on port 3000
- `backend-xrays` - Running on port 3080
- `postgres-xrays` - Running on port 5444

### 2. Test DICOM Files

You'll need sample DICOM files. Download from:

**Option 1: Rubo Medical (Recommended for Quick Testing)**
- URL: https://www.rubomedical.com/dicom_files/
- Download: CT or MR samples (small, fast to test)
- File types: `.dcm` files

**Option 2: TCIA (The Cancer Imaging Archive)**
- URL: https://www.cancerimagingarchive.net/
- More comprehensive datasets
- Requires registration (free)

**Option 3: DICOM Library**
- URL: https://www.dicomlibrary.com/
- Browser-based samples

---

## Test Workflow

### Phase 1: Upload DICOM Files

1. **Open Application**
   ```
   http://localhost:3000
   ```

2. **Login/Register**
   - If not logged in, create an account
   - Navigate to `/tools` page

3. **Upload Files**
   - Click "Upload DICOM" tab
   - Drag and drop DICOM files (or click to browse)
   - Wait for upload confirmation
   - Verify success message appears

**Expected Results:**
- ✅ Files upload successfully
- ✅ Progress indicator shows during upload
- ✅ Success toast notification appears
- ✅ Upload tab shows completion

**If Upload Fails:**
- Check backend logs: `docker logs backend-xrays --tail 50`
- Verify file is valid DICOM (try different sample)
- Check authentication (try logging out and back in)

---

### Phase 2: Browse Studies

1. **Navigate to Browse Tab**
   - Click "Browse Studies" tab

2. **Find Your Study**
   - You should see the uploaded study in the list
   - Check patient name, study date, modality

3. **Verify Study Card**
   - Patient information displayed
   - Study description visible
   - Series count shown
   - Modality badge present

**Expected Results:**
- ✅ Study appears in list immediately
- ✅ All metadata displayed correctly
- ✅ Study card is clickable

**If Study Not Found:**
- Refresh the page
- Check "My Studies" filter
- Verify upload actually succeeded
- Check backend logs for errors

---

### Phase 3: Open Viewer

1. **Click Study Card**
   - Click on the study you uploaded

2. **Wait for Viewer to Load**
   - Loading spinner should appear
   - "Loading viewer..." message shown

3. **Verify Viewer Opens**
   - Black canvas area appears
   - Header shows patient name and study info
   - Right sidebar shows series list
   - Navigation controls visible at bottom

**Expected Results:**
- ✅ Viewer loads within 1-2 seconds
- ✅ No error messages
- ✅ Professional dark theme UI
- ✅ All UI elements visible

**If Viewer Fails to Load:**
- Check browser console (F12) for errors
- Verify backend is running
- Check network tab for failed requests
- Try refreshing page

---

### Phase 4: Test Image Display

This is the critical test for the Cornerstone integration.

1. **Verify First Image Loads**
   - DICOM image should appear on black canvas
   - Loading spinner should disappear
   - Image counter shows "1 / X"

2. **Check Browser Console**
   - Open DevTools (F12)
   - Go to Console tab
   - Look for these messages:
     ```
     Initializing Cornerstone libraries...
     Cornerstone initialized successfully
     Enabling viewport...
     Element enabled for Cornerstone
     Basic tools added and activated
     Viewport enabled successfully
     Loading instances for series 1...
     Displaying image 1: wadouri:http://...
     Loading DICOM image from: http://...
     Image displayed successfully
     ```

3. **Verify Image Quality**
   - Image should be clear and visible
   - Correct window/level applied
   - No pixelation or artifacts
   - Image fills canvas appropriately

**Expected Results:**
- ✅ Image appears within 0.5-2 seconds
- ✅ Image is properly windowed (good contrast)
- ✅ No console errors
- ✅ Image counter shows correct count

**If Image Doesn't Display:**

**Console Error: "Failed to initialize Cornerstone"**
- Refresh page to reinitialize
- Check that Cornerstone libraries loaded
- Verify network connection

**Console Error: "Failed to load image"**
- Check Network tab (F12) for failed requests
- Verify WADO-RS endpoint responding
- Check authentication token
- Backend logs: `docker logs backend-xrays --tail 50`

**Console Error: "Viewport not ready"**
- Wait a few seconds and try navigating to next image
- Refresh page if persists

**Black canvas but no image:**
- Check console for errors
- Verify image ID format is correct
- Check backend WADO-RS endpoint manually:
  ```
  http://localhost:3080/api/dicom/dicom-web/studies/{studyUID}/series/{seriesUID}/instances/{sopUID}/frames/1
  ```

---

### Phase 5: Test Interactive Tools

#### 5.1 Window/Level (Contrast Adjustment)

1. **Left Click and Drag**
   - Click and hold LEFT mouse button on image
   - Drag horizontally (changes window width)
   - Drag vertically (changes window level)

**Expected Results:**
- ✅ Image brightness/contrast changes as you drag
- ✅ Changes are smooth and responsive
- ✅ No lag or stuttering

**Test Cases:**
- Drag left: Image gets darker
- Drag right: Image gets brighter
- Drag up: Contrast increases
- Drag down: Contrast decreases

---

#### 5.2 Zoom Tool

1. **Middle Mouse Button**
   - Click and hold MIDDLE mouse button
   - Drag up to zoom in
   - Drag down to zoom out

2. **Mouse Wheel (Alternative)**
   - Scroll wheel up: Zoom in
   - Scroll wheel down: Zoom out

**Expected Results:**
- ✅ Image zooms smoothly
- ✅ Zoom centers around mouse cursor
- ✅ No distortion or blurriness
- ✅ Can zoom in significantly (200%+)
- ✅ Can zoom out to fit window

**Test Cases:**
- Zoom in to 200%
- Zoom out to 50%
- Zoom at different areas of image
- Verify image quality at different zoom levels

---

#### 5.3 Pan Tool

1. **Right Click and Drag**
   - Click and hold RIGHT mouse button
   - Drag in any direction
   - Image should move with cursor

**Expected Results:**
- ✅ Image pans smoothly
- ✅ No lag or stuttering
- ✅ Can pan in all directions
- ✅ Pan works at any zoom level

**Test Cases:**
- Pan while zoomed in
- Pan to all corners of image
- Pan rapidly to test performance

---

#### 5.4 Reset and Fit

1. **Reset Button**
   - Click "Reset" button (bottom right)
   - OR press SPACE key

**Expected Results:**
- ✅ Image returns to default view
- ✅ Default window/level restored
- ✅ Zoom reset to fit
- ✅ Pan reset to center

2. **Fit Button**
   - Click "Fit" button
   - OR press F key

**Expected Results:**
- ✅ Image resizes to fill viewport
- ✅ Maintains aspect ratio
- ✅ Centers in canvas

---

### Phase 6: Test Navigation

#### 6.1 Image Navigation (Within Series)

1. **Next Image Button**
   - Click "Image ►" button
   - OR press DOWN arrow key

2. **Previous Image Button**
   - Click "◄ Image" button
   - OR press UP arrow key

3. **Mouse Wheel Scroll**
   - Scroll mouse wheel to navigate images

**Expected Results:**
- ✅ New image loads within 0.5-1 second
- ✅ Image counter updates correctly
- ✅ Smooth transition between images
- ✅ Previous/Next buttons disable at endpoints
- ✅ No console errors

**Test Cases:**
- Navigate through all images in series
- Rapid navigation (click Next multiple times)
- Navigate backwards
- Use keyboard shortcuts
- Use mouse wheel

---

#### 6.2 Series Navigation

1. **Next Series Button**
   - Click "Series ►" button
   - OR press RIGHT arrow key

2. **Previous Series Button**
   - Click "◄ Series" button
   - OR press LEFT arrow key

3. **Click Series in Sidebar**
   - Click different series in right sidebar

**Expected Results:**
- ✅ New series loads within 1-2 seconds
- ✅ First image of new series displays
- ✅ Series counter updates
- ✅ Sidebar highlights current series
- ✅ Image counter resets to "1 / X"
- ✅ No console errors

**Test Cases:**
- Navigate to next series
- Navigate back to previous series
- Click series in sidebar
- Verify all series can be loaded

---

### Phase 7: Keyboard Shortcuts

Test all keyboard shortcuts:

| Key | Action | Expected Result |
|-----|--------|----------------|
| ↑ (Up Arrow) | Previous Image | Loads previous image |
| ↓ (Down Arrow) | Next Image | Loads next image |
| ← (Left Arrow) | Previous Series | Loads previous series |
| → (Right Arrow) | Next Series | Loads next series |
| SPACE | Reset Viewport | Resets view to default |
| F | Fit to Window | Fits image to viewport |

**Expected Results:**
- ✅ All shortcuts work immediately
- ✅ No conflicts with browser shortcuts
- ✅ Shortcuts disabled when appropriate

---

### Phase 8: UI/UX Testing

#### 8.1 Tool Info Overlay

- Verify top-left overlay shows:
  ```
  Left Click: Window/Level
  Middle Click: Zoom
  Right Click: Pan
  Mouse Wheel: Scroll Images
  Space: Reset | F: Fit
  ```

#### 8.2 Header Information

- Patient name displayed
- Study description shown
- Patient ID visible
- Series count correct
- Modality badge present

#### 8.3 Loading States

- Spinner appears when loading images
- Loading indicator in header
- No flashing or jarring transitions

#### 8.4 Error Handling

Test error scenarios:
1. Try loading invalid study
2. Disconnect network during load
3. Navigate very rapidly

**Expected Results:**
- ✅ User-friendly error messages
- ✅ No app crashes
- ✅ Can recover from errors

---

## Performance Testing

### Load Times

Measure and verify acceptable performance:

| Operation | Target | Acceptable | Poor |
|-----------|--------|------------|------|
| Viewer Init | <500ms | <1s | >2s |
| First Image Load | <500ms | <1s | >3s |
| Image Navigation | <200ms | <500ms | >1s |
| Series Switch | <500ms | <1s | >2s |
| Tool Response | Instant | <50ms | >100ms |

### Test Cases

1. **Large Series (50+ images)**
   - Upload study with 50+ images
   - Navigate through entire series
   - Verify performance remains good

2. **Large Files (>10MB)**
   - Test with large CT series
   - Monitor memory usage
   - Check for slowdowns

3. **Rapid Navigation**
   - Click Next Image 10 times rapidly
   - Verify no freezing or crashes
   - Check memory doesn't spike

---

## Browser Compatibility

Test in multiple browsers:

### Chrome/Edge (Primary)
- [ ] All features work
- [ ] Tools responsive
- [ ] No console errors
- [ ] Good performance

### Firefox
- [ ] All features work
- [ ] Tools responsive
- [ ] No console errors

### Safari (Mac only)
- [ ] All features work
- [ ] Tools responsive
- [ ] No console errors

**Note**: WebGL support required for optimal performance.

---

## Known Issues & Workarounds

### Issue: First Image Loads Slowly
- **Cause**: Network fetch + DICOM parsing
- **Normal**: First load takes 1-2s
- **Workaround**: None needed, subsequent images cached

### Issue: Tools Not Working
- **Cause**: Cornerstone not initialized
- **Solution**: Refresh page

### Issue: "Failed to load image"
- **Cause**: Backend WADO-RS endpoint issue
- **Check**: Backend logs, authentication
- **Solution**: Restart backend if needed

### Issue: Build Errors (TypeScript)
- **Cause**: zod library version incompatibility
- **Impact**: None (dev server works fine)
- **Solution**: Ignore for now

---

## Success Criteria

### Minimum Viable Product (MVP)

All must pass:
- [x] Upload DICOM files
- [x] Browse studies
- [x] Open viewer
- [x] Display DICOM images on canvas
- [x] Window/Level tool works
- [x] Zoom tool works
- [x] Pan tool works
- [x] Navigate images
- [x] Navigate series
- [x] Reset viewport
- [x] Fit to window
- [x] Keyboard shortcuts work
- [x] No critical errors

### Performance Criteria

- [ ] Image loads in <1s
- [ ] Navigation smooth (<500ms)
- [ ] Tools responsive (no lag)
- [ ] No memory leaks
- [ ] Works in Chrome/Firefox

### Quality Criteria

- [ ] Professional medical UI
- [ ] Clear error messages
- [ ] Intuitive controls
- [ ] No console errors
- [ ] Good documentation

---

## Troubleshooting Reference

### Quick Diagnostics

```bash
# Check all services
docker ps

# Check frontend logs
docker logs frontend-xrays --tail 50

# Check backend logs
docker logs backend-xrays --tail 50

# Restart frontend
docker-compose restart frontend-xrays

# Restart backend
docker-compose restart backend-xrays

# Check network
curl http://localhost:3080/api/health
```

### Browser Console Commands

Open DevTools (F12) and try:

```javascript
// Check Cornerstone loaded
console.log(window.cornerstone);

// Check enabled elements
console.log(cornerstone.getEnabledElements());

// Check image cache
console.log(cornerstone.imageCache.getCacheInfo());
```

---

## Test Report Template

Use this template to document testing results:

```markdown
# Test Report: DICOM Viewer

**Date**: [Date]
**Tester**: [Name]
**Browser**: [Browser + Version]
**OS**: [Operating System]

## Test Results

### Upload: ✅ Pass / ❌ Fail
- Notes: [Any issues or observations]

### Browse: ✅ Pass / ❌ Fail
- Notes:

### Viewer Load: ✅ Pass / ❌ Fail
- Notes:

### Image Display: ✅ Pass / ❌ Fail
- Notes:

### Window/Level: ✅ Pass / ❌ Fail
- Notes:

### Zoom: ✅ Pass / ❌ Fail
- Notes:

### Pan: ✅ Pass / ❌ Fail
- Notes:

### Navigation: ✅ Pass / ❌ Fail
- Notes:

### Keyboard Shortcuts: ✅ Pass / ❌ Fail
- Notes:

### Performance: ✅ Pass / ❌ Fail
- First load: [time]
- Navigation: [time]
- Notes:

## Issues Found

1. [Issue description]
   - Severity: Critical/High/Medium/Low
   - Steps to reproduce:
   - Expected vs Actual:

## Overall Assessment

✅ Ready for Production / ⚠️ Needs Fixes / ❌ Major Issues

Notes: [Summary]
```

---

## Next Steps After Testing

### If All Tests Pass ✅

1. **Document any observations**
2. **Plan advanced features**:
   - Measurement tools
   - Annotations
   - MPR (Multi-planar reconstruction)
   - 3D rendering
3. **Production deployment preparation**

### If Tests Fail ❌

1. **Document exact failure**
2. **Check browser console for errors**
3. **Review backend logs**
4. **Create GitHub issue if needed**
5. **Request support**

---

## Support

**Documentation**:
- Implementation: `CORNERSTONE-IMPLEMENTATION-COMPLETE.md`
- Project Overview: `OHIF-PROJECT-SUMMARY.md`
- Next Steps: `NEXT-STEPS-CORNERSTONE.md`

**Logs**:
- Frontend: `docker logs frontend-xrays`
- Backend: `docker logs backend-xrays`

**URLs**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:3080
- WADO-RS: http://localhost:3080/api/dicom/dicom-web/

---

**Document Version**: 1.0
**Status**: Ready for Testing
**Expected Testing Time**: 30-45 minutes for complete test suite
