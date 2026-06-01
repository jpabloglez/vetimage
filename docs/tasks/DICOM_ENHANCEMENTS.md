# DICOM Data Management System - Feature Documentation

## Overview

This document describes the enhanced DICOM data management system that provides comprehensive tag storage, thumbnail generation, advanced search capabilities, and annotation tools with automatic measurement calculations.

---

## Table of Contents

1. [Features](#features)
2. [API Endpoints](#api-endpoints)
3. [Usage Examples](#usage-examples)
4. [Data Models](#data-models)
5. [Testing Guide](#testing-guide)

---

## Features

### 1. Comprehensive DICOM Tag Storage

All DICOM tags are now automatically extracted and stored in JSON format during upload:

- **Complete metadata preservation**: Every DICOM tag is captured
- **Searchable normalized fields**: Patient names and descriptions are normalized for fast searching
- **Technical parameters**: Pixel spacing, slice location, window/level defaults
- **Pixel value ranges**: Hounsfield units for CT images

### 2. Series Thumbnails

Three sizes of thumbnails are automatically available:

- **Small** (150x150px): For list views and thumbnails
- **Medium** (300x300px): For preview cards
- **Large** (512x512px): For quick preview modals

**Features**:
- Lazy generation (created on first access)
- Proper DICOM windowing applied
- Middle slice used for multi-slice series
- Status tracking (pending/processing/completed/failed)

### 3. Advanced Search

Powerful search capabilities with multiple filter criteria:

- **Text search**: Patient name, patient ID, study description (case-insensitive)
- **Date ranges**: Filter by study date
- **Modality filtering**: Search by modality (CT, MR, CR, etc.)
- **Body part**: Filter by anatomical region
- **Pagination**: Limit and offset support

**Saved Searches**:
- Save frequently used search queries
- Execute saved searches with one click
- Usage statistics tracking

### 4. Image Annotations

Rich annotation system with automatic measurements:

**Annotation Types**:
- Text labels
- Arrows
- Rectangles
- Ellipses
- Polygons
- Lines
- **Distance measurements** (automatically calculated in mm or pixels)
- **Area measurements** (automatically calculated in mm² or pixels²)
- **Angle measurements** (automatically calculated in degrees)
- Regions of Interest (ROI)

**Features**:
- Multi-frame support
- Automatic measurement calculations using pixel spacing
- Visibility levels (private/shared/public)
- Annotation templates for reusable styles

---

## API Endpoints

### Thumbnail Endpoints

#### Get Series Thumbnail
```http
GET /api/dicom/series/{series_uid}/thumbnail/{size}/
```

**Parameters**:
- `series_uid`: Series Instance UID
- `size`: `small` | `medium` | `large`

**Response**: JPEG image

**Example**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:3080/api/dicom/series/1.2.840.113619.2.55.../thumbnail/medium/ \
  > thumbnail.jpg
```

#### Generate Thumbnails Manually
```http
POST /api/dicom/series/{series_uid}/generate-thumbnails/
```

**Response**:
```json
{
  "success": true,
  "message": "Thumbnails generated successfully",
  "thumbnail_urls": {
    "small": "http://.../media/thumbnails/.../small/...",
    "medium": "http://.../media/thumbnails/.../medium/...",
    "large": "http://.../media/thumbnails/.../large/..."
  }
}
```

---

### Advanced Search Endpoints

#### Advanced Search
```http
POST /api/dicom/search/advanced/
Content-Type: application/json

{
  "patient_name": "John",
  "patient_id": "12345",
  "study_description": "chest",
  "modality": ["CT", "CR"],
  "date_from": "2024-01-01",
  "date_to": "2024-12-31",
  "body_part": "chest",
  "limit": 50,
  "offset": 0
}
```

**Response**:
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "results": [
    {
      "id": 1,
      "study_instance_uid": "1.2.840...",
      "patient_id": "12345",
      "patient_name": "JOHN^DOE",
      "study_date": "2024-06-15",
      "study_description": "CHEST CT",
      "uploaded_at": "2024-06-15T10:30:00Z",
      "number_of_series": 3,
      "number_of_instances": 120
    }
  ]
}
```

#### List Saved Searches
```http
GET /api/dicom/search/saved/
```

#### Create Saved Search
```http
POST /api/dicom/search/saved/
Content-Type: application/json

{
  "name": "Chest CTs from 2024",
  "description": "All chest CT studies from 2024",
  "search_filters": {
    "modality": ["CT"],
    "body_part": "chest",
    "date_from": "2024-01-01",
    "date_to": "2024-12-31"
  }
}
```

#### Execute Saved Search
```http
GET /api/dicom/search/saved/{search_id}/?execute=true
```

---

### Annotation Endpoints

#### List Annotations for Image
```http
GET /api/dicom/images/{sop_uid}/annotations/?frame=0
```

**Response**:
```json
[
  {
    "id": 1,
    "image": 123,
    "image_sop_uid": "1.2.840...",
    "annotation_type": "distance",
    "frame_number": 0,
    "geometry_data": {
      "points": [
        {"x": 100, "y": 150},
        {"x": 200, "y": 250}
      ]
    },
    "measurement_value": 45.3,
    "measurement_unit": "mm",
    "label": "Tumor diameter",
    "description": "Measuring primary lesion",
    "visibility": "private",
    "created_by_email": "user@example.com",
    "created_at": "2024-06-15T14:30:00Z",
    "updated_at": "2024-06-15T14:30:00Z"
  }
]
```

#### Create Distance Annotation
```http
POST /api/dicom/images/{sop_uid}/annotations/
Content-Type: application/json

{
  "annotation_type": "distance",
  "frame_number": 0,
  "geometry_data": {
    "points": [
      {"x": 100, "y": 150},
      {"x": 200, "y": 250}
    ]
  },
  "label": "Tumor diameter",
  "description": "Measuring primary lesion",
  "visibility": "private"
}
```

**Automatic Calculation**: The system automatically calculates the distance using pixel spacing if available, otherwise uses pixel units.

#### Create Area Annotation
```http
POST /api/dicom/images/{sop_uid}/annotations/
Content-Type: application/json

{
  "annotation_type": "area",
  "frame_number": 0,
  "geometry_data": {
    "points": [
      {"x": 100, "y": 100},
      {"x": 200, "y": 100},
      {"x": 200, "y": 200},
      {"x": 100, "y": 200}
    ]
  },
  "label": "ROI Area",
  "visibility": "shared"
}
```

**Automatic Calculation**: Area is calculated using the Shoelace formula and converted to mm² if pixel spacing is available.

#### Create Angle Annotation
```http
POST /api/dicom/images/{sop_uid}/annotations/
Content-Type: application/json

{
  "annotation_type": "angle",
  "frame_number": 0,
  "geometry_data": {
    "points": [
      {"x": 50, "y": 100},
      {"x": 100, "y": 100},
      {"x": 150, "y": 50}
    ]
  },
  "label": "Joint angle",
  "visibility": "private"
}
```

**Automatic Calculation**: Angle is calculated in degrees between the three points (vertex at second point).

#### Update Annotation
```http
PUT /api/dicom/annotations/{annotation_id}/
Content-Type: application/json

{
  "label": "Updated label",
  "description": "Updated description"
}
```

**Note**: Measurements are automatically recalculated if `geometry_data` is updated.

#### Delete Annotation
```http
DELETE /api/dicom/annotations/{annotation_id}/
```

---

## Data Models

### DICOM Tags Storage Format

Tags are stored in JSON with the following structure:

```json
{
  "00100020": {
    "vr": "LO",
    "name": "Patient ID",
    "value": "12345"
  },
  "00100010": {
    "vr": "PN",
    "name": "Patient Name",
    "value": "DOE^JOHN"
  },
  "00080060": {
    "vr": "CS",
    "name": "Modality",
    "value": "CT"
  }
}
```

### Annotation Geometry Data Formats

**Distance (2 points)**:
```json
{
  "points": [
    {"x": 100, "y": 150},
    {"x": 200, "y": 250}
  ]
}
```

**Area (polygon with 3+ points)**:
```json
{
  "points": [
    {"x": 100, "y": 100},
    {"x": 200, "y": 100},
    {"x": 200, "y": 200},
    {"x": 100, "y": 200}
  ]
}
```

**Angle (exactly 3 points, vertex at second point)**:
```json
{
  "points": [
    {"x": 50, "y": 100},
    {"x": 100, "y": 100},
    {"x": 150, "y": 50}
  ]
}
```

**Text Label**:
```json
{
  "position": {"x": 100, "y": 200},
  "text": "Finding here",
  "fontSize": 14
}
```

---

## Testing Guide

### 1. Upload DICOM Files

The enhanced upload automatically extracts all metadata:

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -F "file=@chest_ct_001.dcm" \
  http://localhost:3080/api/dicom/upload/
```

**What happens**:
- All DICOM tags extracted to JSON
- Pixel spacing, slice info captured
- Text fields normalized for search
- Series marked for thumbnail generation

### 2. Test Advanced Search

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "john",
    "modality": ["CT"],
    "date_from": "2024-01-01",
    "limit": 10
  }' \
  http://localhost:3080/api/dicom/search/advanced/
```

### 3. Generate and Retrieve Thumbnails

```bash
# Get thumbnail (auto-generates if not exists)
curl -H "Authorization: Bearer <token>" \
  http://localhost:3080/api/dicom/series/1.2.840.../thumbnail/medium/ \
  > thumbnail.jpg

# Manually trigger generation
curl -X POST \
  -H "Authorization: Bearer <token>" \
  http://localhost:3080/api/dicom/series/1.2.840.../generate-thumbnails/
```

### 4. Create Annotations with Measurements

```bash
# Distance measurement
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "annotation_type": "distance",
    "frame_number": 0,
    "geometry_data": {
      "points": [
        {"x": 100, "y": 100},
        {"x": 200, "y": 200}
      ]
    },
    "label": "Test measurement"
  }' \
  http://localhost:3080/api/dicom/images/1.2.840.../annotations/
```

**Expected Response**:
```json
{
  "id": 1,
  "annotation_type": "distance",
  "measurement_value": 141.42,
  "measurement_unit": "pixels",
  "label": "Test measurement",
  ...
}
```

If the image has pixel spacing (e.g., 0.5mm x 0.5mm), the measurement would be in mm instead.

### 5. Save and Execute Searches

```bash
# Save a search
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Chest CTs",
    "search_filters": {
      "modality": ["CT"],
      "body_part": "chest"
    }
  }' \
  http://localhost:3080/api/dicom/search/saved/

# Execute saved search
curl -H "Authorization: Bearer <token>" \
  "http://localhost:3080/api/dicom/search/saved/1/?execute=true"
```

---

## Performance Considerations

### Thumbnails
- **Lazy generation**: Thumbnails are only created when first requested
- **Cached**: Once generated, thumbnails are served directly from storage
- **Background processing**: Consider using Celery for async generation in production

### Search
- **Indexed fields**: All normalized text fields and commonly queried fields are indexed
- **Pagination**: Always use limit/offset for large result sets
- **Date filters**: Date range queries are optimized with database indexes

### DICOM Tags
- **JSON storage**: PostgreSQL JSONB recommended for better query performance
- **Selective retrieval**: Tags can be queried without loading full objects

---

## Migration Notes

The migration `0002_medicalimage_dicom_tags_medicalimage_max_pixel_value_and_more.py` adds:
- JSONField columns (SQLite uses TEXT, PostgreSQL should use JSONB)
- Multiple float/integer columns for technical parameters
- Three ImageField columns for thumbnails per series
- New tables for SavedSearch, ImageAnnotation, AnnotationTemplate

**Storage Requirements**:
- DICOM tags: ~5-20 KB per image (varies by modality)
- Thumbnails: ~10-50 KB per size per series
- Annotations: ~1-5 KB per annotation

---

## Future Enhancements

Potential additions for future iterations:

1. **Celery Integration**: Background thumbnail generation
2. **PostgreSQL Migration**: For JSONB performance benefits
3. **Full-text Search**: PostgreSQL full-text search on descriptions
4. **3D Annotations**: Support for volumetric annotations
5. **AI Integration**: Automatic ROI detection and measurements
6. **Export Features**: Export annotations to DICOM SR or PDF reports
7. **Comparison Tools**: Side-by-side measurement comparisons
8. **Collaboration**: Real-time annotation sharing

---

## Support

For issues or questions:
- Check logs: `docker-compose logs backend-xrays`
- Verify migrations: `make migrate`
- Test endpoints with the examples above
- Review model definitions in `dicom_images/models.py`
