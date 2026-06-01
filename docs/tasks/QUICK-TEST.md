# Quick Test - 5 Minute Verification

**Purpose**: Rapid verification that Cornerstone viewer works
**Time**: 5 minutes
**Date**: 2025-12-21

---

## Prerequisites

1. **Download ONE sample DICOM file**:
   - Go to: https://www.rubomedical.com/dicom_files/
   - Download: `chest.dcm` (chest X-ray)
   - Save to your Downloads folder

2. **Services running**:
   ```bash
   docker ps
   ```
   Should show: `frontend-xrays`, `backend-xrays`, `postgres-xrays`

---

## 5-Minute Test

### Step 1: Open Application (30 seconds)

1. Open browser: http://localhost:3000
2. Login or register (if needed)
3. Navigate to: http://localhost:3000/tools

✅ **Success**: You see the Tools page with tabs

---

### Step 2: Upload DICOM (1 minute)

1. Click **"Upload DICOM"** tab
2. Drag `chest.dcm` file onto upload area
3. Wait for upload to complete
4. Look for success message

✅ **Success**: Green toast notification "Files uploaded successfully"

---

### Step 3: Browse Study (30 seconds)

1. Click **"Browse Studies"** tab
2. Find the uploaded study (should be first)
3. Verify you see:
   - Patient name
   - Study date
   - Modality (DX or CR)

✅ **Success**: Study card is visible and clickable

---

### Step 4: Open Viewer (30 seconds)

1. Click the study card
2. Wait for viewer to load
3. Viewer should open with:
   - Black canvas area
   - Patient info in header
   - Series list on right
   - Controls at bottom

✅ **Success**: Viewer interface loads

---

### Step 5: Verify Image Display (1 minute)

**This is the critical test!**

1. **Look at the canvas**:
   - You should see the chest X-ray image
   - Image should be clear and visible
   - NOT a broken image icon
   - NOT a blank black canvas

2. **Open Browser Console (F12)**:
   - Press F12 to open DevTools
   - Click "Console" tab
   - Look for these messages:
     ```
     Cornerstone initialized successfully
     Viewport enabled successfully
     Image displayed successfully
     ```
   - Should see NO red errors

✅ **Success**: X-ray image visible on canvas + no console errors

---

### Step 6: Test Tools (2 minutes)

#### Window/Level (30 seconds)
1. Click and hold LEFT mouse button on image
2. Drag left/right
3. Image brightness should change in real-time

✅ **Success**: Image gets brighter/darker as you drag

#### Zoom (30 seconds)
1. Middle-click and drag up (or scroll wheel up)
2. Image should zoom in
3. Drag down to zoom out

✅ **Success**: Image zooms smoothly

#### Pan (30 seconds)
1. Right-click and hold
2. Drag image around
3. Image should move with cursor

✅ **Success**: Image pans smoothly

#### Reset (15 seconds)
1. Press SPACE key
2. Image should return to default view

✅ **Success**: View resets

---

## Results

### ✅ ALL TESTS PASSED

**Congratulations!** Your Cornerstone DICOM viewer is fully functional.

**What works**:
- ✅ DICOM upload
- ✅ Study browsing
- ✅ Image rendering on canvas
- ✅ Interactive tools (window/level, zoom, pan)
- ✅ Keyboard shortcuts

**Next steps**:
1. Test with more complex studies (CT series with 50+ images)
2. Test with different modalities (MR, CT)
3. Review full testing guide: `TESTING-GUIDE.md`
4. Consider adding advanced features (measurements, annotations)

---

### ❌ TESTS FAILED

If any test failed, check:

**Image doesn't display?**
```bash
# Check backend logs
docker logs backend-xrays --tail 50

# Check frontend logs
docker logs frontend-xrays --tail 30

# Check browser console (F12)
# Look for errors in red
```

**Tools don't work?**
- Refresh page (Cmd+R / Ctrl+R)
- Check console for errors
- Verify image is actually loaded

**Study doesn't appear?**
- Verify upload succeeded
- Try refreshing Browse tab
- Check backend is running: `docker ps`

**For detailed troubleshooting**, see: `TESTING-GUIDE.md`

---

## Quick Diagnostic Commands

```bash
# Check all services healthy
docker ps

# View recent frontend logs
docker logs frontend-xrays --tail 30

# View recent backend logs
docker logs backend-xrays --tail 30

# Restart frontend
docker-compose restart frontend-xrays

# Restart backend
docker-compose restart backend-xrays
```

---

## Console Checks

Open browser console (F12) and verify:

**Good signs** ✅:
```
Cornerstone initialized successfully
Viewport enabled successfully
Loading instances for series 1...
Image displayed successfully
```

**Bad signs** ❌:
```
Failed to initialize Cornerstone
Failed to load image
TypeError: Cannot read property...
```

If you see bad signs, screenshot and check full documentation.

---

## Performance Benchmarks

Expected performance for single image:

| Operation | Time | Status |
|-----------|------|--------|
| Viewer load | <1s | ✅ Normal |
| Image display | <1s | ✅ Normal |
| Tool response | Instant | ✅ Normal |

If slower:
- First load is always slower (network + parsing)
- Subsequent images load faster (caching)
- Large files (>10MB) may take 2-3s

---

## Sample DICOM Files

### Quick Testing (Single Images)
- **Rubo Medical**: https://www.rubomedical.com/dicom_files/
  - chest.dcm (X-ray)
  - brain_001.dcm (CT slice)

### Advanced Testing (Series)
- **TCIA**: https://www.cancerimagingarchive.net/
  - Full CT/MR series (50+ images)
  - Requires free registration

---

## Success Checklist

Minimum viable test:
- [ ] Application loads
- [ ] Can upload DICOM file
- [ ] Study appears in browse list
- [ ] Viewer opens
- [ ] **Image displays on canvas** ← Most important!
- [ ] Window/level works
- [ ] Zoom works
- [ ] Pan works
- [ ] No console errors

**If all checked**: 🎉 Implementation successful!

---

## What to Report

If everything works:
```
✅ Quick test passed!
- Image displays correctly
- Tools work smoothly
- Performance good
Ready for advanced features.
```

If something fails:
```
❌ Issue found:
- Step that failed: [Step X]
- What happened: [Description]
- Console errors: [Copy errors]
- Screenshots: [Attach if possible]
```

---

**Document Version**: 1.0
**Expected Time**: 5 minutes
**Complexity**: Beginner-friendly
**Status**: Ready to use now

**Start testing**: Download chest.dcm and follow Step 1!
