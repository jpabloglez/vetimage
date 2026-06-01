# DICOM API Quick Reference

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

## Base URL

```
http://localhost:3080/api/dicom
```

---

## 📤 Upload & Storage

### Upload DICOM Files
```http
POST /upload/
Content-Type: multipart/form-data
```

### Get Storage Quota
```http
GET /storage/
```

---

## 🔍 Search & Query

### List All Studies (DICOMweb)
```http
GET /dicom-web/studies
```

### Advanced Search
```http
POST /search/advanced/
Body: {
  "patient_name": "string",
  "patient_id": "string",
  "study_description": "string",
  "modality": ["CT", "MR"],
  "date_from": "YYYY-MM-DD",
  "date_to": "YYYY-MM-DD",
  "body_part": "string",
  "limit": 50,
  "offset": 0
}
```

### Saved Searches
```http
GET    /search/saved/              # List all
POST   /search/saved/              # Create new
GET    /search/saved/{id}/         # Get details
GET    /search/saved/{id}/?execute=true  # Execute search
PUT    /search/saved/{id}/         # Update
DELETE /search/saved/{id}/         # Delete
```

---

## 🖼️ Thumbnails

### Get Thumbnail
```http
GET /series/{series_uid}/thumbnail/{size}/
```
Sizes: `small` | `medium` | `large`

### Generate Thumbnails
```http
POST /series/{series_uid}/generate-thumbnails/
```

---

## ✏️ Annotations

### List Annotations
```http
GET /images/{sop_uid}/annotations/?frame={frame_number}
```

### Create Annotation
```http
POST /images/{sop_uid}/annotations/
Body: {
  "annotation_type": "distance|area|angle|text|arrow|rectangle|ellipse|polygon|line|roi",
  "frame_number": 0,
  "geometry_data": { /* See below */ },
  "label": "string",
  "description": "string",
  "visibility": "private|shared|public"
}
```

### Get/Update/Delete Annotation
```http
GET    /annotations/{id}/
PUT    /annotations/{id}/
DELETE /annotations/{id}/
```

---

## 📐 Geometry Data Examples

### Distance (2 points)
```json
{
  "points": [
    {"x": 100, "y": 150},
    {"x": 200, "y": 250}
  ]
}
```
**Auto-calculates**: Distance in mm (if pixel spacing available) or pixels

### Area (polygon)
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
**Auto-calculates**: Area in mm² or pixels²

### Angle (3 points, vertex at middle)
```json
{
  "points": [
    {"x": 50, "y": 100},
    {"x": 100, "y": 100},
    {"x": 150, "y": 50}
  ]
}
```
**Auto-calculates**: Angle in degrees

### Text Label
```json
{
  "position": {"x": 100, "y": 200},
  "text": "Finding here",
  "fontSize": 14
}
```

---

## 🗂️ DICOMweb Endpoints (OHIF Compatible)

### QIDO-RS (Query)
```http
GET /dicom-web/studies
GET /dicom-web/studies/{study_uid}/series
GET /dicom-web/studies/{study_uid}/series/{series_uid}/instances
```

### WADO-RS (Retrieve)
```http
GET /dicom-web/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}/frames/{frame}
GET /dicom-web/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}
```

### Metadata
```http
GET /dicom-web/studies/{study_uid}/metadata
GET /dicom-web/studies/{study_uid}/series/{series_uid}/metadata
GET /dicom-web/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}/metadata
```

---

## 🗑️ Study Management

### Delete Study
```http
DELETE /studies/{study_uid}
```

---

## 📊 Response Formats

### Successful Response
```json
{
  "success": true,
  "message": "Operation completed",
  "data": { /* response data */ }
}
```

### Error Response
```json
{
  "error": "Error message",
  "details": { /* additional error info */ }
}
```

### Paginated Response
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "results": [ /* array of items */ ]
}
```

---

## 🚀 Quick Start Examples

### Python
```python
import requests

BASE_URL = "http://localhost:3080/api/dicom"
TOKEN = "your_jwt_token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Upload DICOM
with open("image.dcm", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/upload/",
        files={"file": f},
        headers=HEADERS
    )

# Search studies
response = requests.post(
    f"{BASE_URL}/search/advanced/",
    json={"patient_name": "john", "modality": ["CT"]},
    headers=HEADERS
)

# Get thumbnail
response = requests.get(
    f"{BASE_URL}/series/1.2.840.../thumbnail/medium/",
    headers=HEADERS
)
with open("thumbnail.jpg", "wb") as f:
    f.write(response.content)

# Create distance annotation
response = requests.post(
    f"{BASE_URL}/images/1.2.840.../annotations/",
    json={
        "annotation_type": "distance",
        "frame_number": 0,
        "geometry_data": {
            "points": [
                {"x": 100, "y": 100},
                {"x": 200, "y": 200}
            ]
        },
        "label": "Measurement"
    },
    headers=HEADERS
)
```

### JavaScript (fetch)
```javascript
const BASE_URL = 'http://localhost:3080/api/dicom';
const TOKEN = 'your_jwt_token';
const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// Advanced search
const searchResponse = await fetch(`${BASE_URL}/search/advanced/`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    patient_name: 'john',
    modality: ['CT'],
    limit: 10
  })
});
const searchResults = await searchResponse.json();

// Create annotation
const annotationResponse = await fetch(
  `${BASE_URL}/images/1.2.840.../annotations/`,
  {
    method: 'POST',
    headers,
    body: JSON.stringify({
      annotation_type: 'distance',
      frame_number: 0,
      geometry_data: {
        points: [
          {x: 100, y: 100},
          {x: 200, y: 200}
        ]
      },
      label: 'Measurement'
    })
  }
);
const annotation = await annotationResponse.json();
console.log('Distance:', annotation.measurement_value, annotation.measurement_unit);
```

### cURL
```bash
# Search
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_name":"john","modality":["CT"]}' \
  http://localhost:3080/api/dicom/search/advanced/

# Get thumbnail
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:3080/api/dicom/series/1.2.840.../thumbnail/medium/ \
  > thumbnail.jpg

# Create annotation
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "annotation_type": "distance",
    "frame_number": 0,
    "geometry_data": {
      "points": [{"x":100,"y":100},{"x":200,"y":200}]
    },
    "label": "Test"
  }' \
  http://localhost:3080/api/dicom/images/1.2.840.../annotations/
```

---

## ⚠️ Important Notes

1. **Authentication Required**: All endpoints require valid JWT token
2. **Automatic Measurements**: Distance/area/angle annotations auto-calculate on create/update
3. **Lazy Thumbnails**: Generated on first access (may take a few seconds initially)
4. **Pixel Spacing**: Measurements use mm when pixel spacing available, otherwise pixels
5. **Visibility**: Annotations have private/shared/public visibility levels
6. **Frame Support**: Multi-frame images supported via `frame_number` parameter
7. **CORS**: Ensure CORS is configured for your frontend domain

---

## 🔧 Status Codes

- `200` - Success
- `201` - Created
- `204` - No Content (successful deletion)
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `413` - Payload Too Large (exceeds quota)
- `500` - Internal Server Error
