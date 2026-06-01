# Orthanc Test PACS - Configuration Guide

## Overview

The Orthanc Test PACS is configured to work seamlessly with the OpenMedLab DICOM Gateway for testing and development purposes.

## Configuration Summary

### System Information
- **Name**: OpenMedLab Test PACS
- **Version**: 1.12.5
- **DICOM AE Title**: ORTHANC
- **DICOM Port**: 4242
- **HTTP Port**: 8042
- **Credentials**: `orthanc` / `orthanc`

### Web Interfaces

#### Orthanc Explorer 2 (Primary UI)
- **URL**: http://localhost:8042/ui/app/
- **Status**: ✅ Enabled and configured as default UI
- **Features**:
  - Modern, responsive interface
  - Upload DICOM files via drag-and-drop
  - Send studies to configured modalities (including Gateway)
  - Download studies, anonymize, modify
  - API view menu for developers
  - Settings management

#### Classic Orthanc Explorer
- **URL**: http://localhost:8042/app/explorer.html
- **Status**: ✅ Available as fallback

### DICOM Connectivity

#### Configured Modalities

**OPENMEDLAB Gateway**
- **AE Title**: OPENMEDLAB
- **Host**: dicom-gateway-openmedlab (Docker service name)
- **Port**: 11112
- **Capabilities**: C-ECHO, C-STORE, C-FIND, C-MOVE, C-GET
- **Status**: ✅ Connected and tested

### Testing Commands

#### Verify Orthanc Status
```bash
make orthanc-status
```

#### List Configured Modalities
```bash
make orthanc-modalities
```

#### Test DICOM Connectivity (C-ECHO)
```bash
make orthanc-echo-gateway
```

#### List Studies in Orthanc
```bash
make orthanc-studies
```

#### Send Study to Gateway
```bash
# First, get the study ID from orthanc-studies
make orthanc-send-study STUDY_ID=<study-uuid>
```

#### Open Orthanc Web Interface
```bash
make orthanc-open
```

## Configuration Files

### Primary Configuration
**File**: `/home/jpablo/code/web-apps/openmedlab/setup/orthanc.json`

**Key Settings**:
```json
{
  "Name": "OpenMedLab Test PACS",
  "DicomAet": "ORTHANC",
  "DicomPort": 4242,
  "HttpPort": 8042,

  "Plugins": [
    "/usr/local/share/orthanc/plugins"
  ],

  "DicomModalities": {
    "OPENMEDLAB": ["OPENMEDLAB", "dicom-gateway-openmedlab", 11112]
  },

  "OrthancExplorer2": {
    "IsDefaultOrthancUI": true,
    "UiOptions": {
      "EnableUpload": true,
      "EnableAnonymize": true,
      "EnableModify": true,
      "EnableDeleteResources": true,
      "EnableApiViewMenu": true
    }
  },

  "RegisteredUsers": {
    "orthanc": "orthanc"
  }
}
```

## Sending DICOM Files to Gateway

### Method 1: Via Orthanc Explorer 2 (Web UI)

1. Open http://localhost:8042/ui/app/
2. Login with credentials: `orthanc` / `orthanc`
3. Upload DICOM files:
   - Click "Upload" button
   - Drag and drop DICOM files or select from file browser
4. Send to Gateway:
   - Navigate to uploaded study
   - Click "Send to modality" button
   - Select "OPENMEDLAB" from the list
   - Confirm sending

### Method 2: Via REST API

```bash
# 1. Upload DICOM file to Orthanc
curl -X POST http://localhost:8042/instances \
  -u orthanc:orthanc \
  --data-binary @/path/to/file.dcm

# 2. Get study ID from response
STUDY_ID="<study-instance-uid>"

# 3. Send to Gateway
curl -X POST http://localhost:8042/modalities/OPENMEDLAB/store \
  -u orthanc:orthanc \
  -d '{"Resources":["'"$STUDY_ID"'"],"Synchronous":false}'
```

### Method 3: Via Makefile Commands

```bash
# Send specific study
make orthanc-send-study STUDY_ID=<study-uuid>
```

## Loaded Plugins

The following plugins are available and loaded:

- **orthanc-explorer-2**: Modern web interface
- **dicom-web**: DICOMweb (QIDO-RS, WADO-RS, STOW-RS) support
- **ohif**: OHIF viewer integration
- **volview**: 3D volume viewer
- **stone-webviewer**: Stone web viewer
- **worklists**: DICOM worklist support
- **postgresql-index**: PostgreSQL database backend
- **mysql-index**: MySQL database backend
- **AWS S3 Storage**: Object storage support
- **housekeeper**: Automated maintenance tasks

## Workflow: Orthanc → Gateway → Backend

```
┌──────────────────┐
│  Upload DICOM    │
│  to Orthanc      │
│  (Web UI / API)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Orthanc Test PACS│
│ Port: 8042, 4242 │
└────────┬─────────┘
         │ C-STORE (DICOM protocol)
         │ AE: OPENMEDLAB
         │ Host: dicom-gateway-openmedlab:11112
         ▼
┌──────────────────┐
│ DICOM Gateway    │
│ Receives images  │
│ Extracts metadata│
└────────┬─────────┘
         │ HTTP POST
         │ /api/dicom/upload/
         ▼
┌──────────────────┐
│ Django Backend   │
│ Stores in DB     │
│ Creates tasks    │
└──────────────────┘
```

## Troubleshooting

### Issue: Can't connect to Gateway

**Check 1**: Verify Gateway is running
```bash
make gateway-status
```

**Check 2**: Test C-ECHO
```bash
make orthanc-echo-gateway
```

**Check 3**: Check Gateway logs
```bash
make logs-gateway
```

### Issue: Orthanc Explorer 2 not showing

**Solution**: Ensure configuration has:
```json
"OrthancExplorer2": {
  "IsDefaultOrthancUI": true
}
```

Then restart Orthanc:
```bash
docker-compose up -d --force-recreate orthanc-test-pacs
```

### Issue: Authentication fails

**Default credentials**:
- Username: `orthanc`
- Password: `orthanc`

Configured in `orthanc.json`:
```json
"RegisteredUsers": {
  "orthanc": "orthanc"
}
```

## Security Considerations

⚠️ **For Development/Testing Only**

- Default credentials (`orthanc`/`orthanc`) should be changed in production
- Remote access is enabled - restrict network access in production
- SSL/TLS is not enabled - use reverse proxy with HTTPS in production
- DICOM TLS is disabled - enable for production deployments

## Performance Tuning

Current settings optimized for development:

- **Concurrent Jobs**: 2
- **DICOM Threads**: 4
- **HTTP Threads**: 50
- **Storage**: File-based (SQLite database)
- **Compression**: Disabled for faster performance

For production, consider:
- PostgreSQL/MySQL database backend
- Storage compression enabled
- Increased thread counts based on workload
- Load balancing for high availability

## Related Documentation

- [DICOM Gateway Evaluation](./DICOM-Gateway-Evaluation.md)
- [Orthanc Book](https://orthanc.uclouvain.be/book/)
- [Orthanc Explorer 2 Documentation](https://orthanc.uclouvain.be/book/plugins/orthanc-explorer-2.html)
- [DICOMweb Plugin](https://orthanc.uclouvain.be/book/plugins/dicomweb.html)
