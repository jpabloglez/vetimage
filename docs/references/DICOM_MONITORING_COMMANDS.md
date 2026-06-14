# Real-Time DICOM Transfer Monitoring Commands

## Quick Status Check

Run these commands to verify the complete workflow:

### 1. Check DICOM Gateway Reception
```bash
# Watch for incoming C-STORE requests
docker-compose logs -f dicom-gateway-openmedlab | grep "C-STORE"
```

**Expected Output:**
```
C-STORE received: Patient=..., Study=1.2.276..., Series=..., Instance=...
C-STORE completed in 8.45ms
```

### 2. Monitor Celery Task Processing
```bash
# Watch celery worker process files
docker-compose logs -f gateway-celery-worker | grep -E "process_dicom_file|Task|SUCCESS|FAIL"
```

**Expected Output:**
```
[INFO] Task gateway.tasks.process_dicom_file[...] received
[INFO] Processing DICOM file: /app/storage/...
[INFO] Uploaded to backend: {...}
[INFO] Task gateway.tasks.process_dicom_file[...] succeeded
```

### 3. Check Transaction Creation in Database
```bash
# Count transactions in database
docker exec backend-openmedlab python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from dicom_gateway.models import DICOMTransaction
print(f'Total transactions: {DICOMTransaction.objects.count()}')
for t in DICOMTransaction.objects.all().order_by('-started_at')[:5]:
    print(f'  - Study: {t.study_instance_uid[:40]}...')
    print(f'    Status: {t.status}, Time: {t.started_at}')
"
```

**Expected Output:**
```
Total transactions: 15
  - Study: 1.2.276.0.7230010.3.1.2.4087122745...
    Status: success, Time: 2026-01-05 18:50:00+00:00
```

### 4. Test Monitor API Endpoint
```bash
# Check if API returns data
docker exec backend-openmedlab python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from dicom_gateway.views import DICOMTransferViewSet

User = get_user_model()
user = User.objects.first()

factory = RequestFactory()
request = factory.get('/api/dicom-gateway/transfers/monitor/')
request.user = user

view = DICOMTransferViewSet.as_view({'get': 'monitor'})
response = view(request)

print(f'Monitor API Status: {response.status_code}')
print(f'Transfer count: {response.data.get(\"count\", 0) if hasattr(response, \"data\") else \"N/A\"}')
"
```

### 5. Check Files in Storage
```bash
# List recently received files
docker exec dicom-gateway-openmedlab find /app/storage/dicom-temp -name "*.dcm" -mmin -5 -ls
```

---

## Complete Workflow Test

### Step 1: Send from Orthanc
1. Open Orthanc web interface: `http://localhost:8042`
2. Select any study
3. Click "Send to DICOM modality"
4. Select "OPENMEDLAB"
5. Click "Send"

### Step 2: Monitor (run in separate terminals)

**Terminal 1 - Gateway Logs:**
```bash
docker-compose logs -f --tail=0 dicom-gateway-openmedlab
```

**Terminal 2 - Celery Worker:**
```bash
docker-compose logs -f --tail=0 gateway-celery-worker
```

**Terminal 3 - Backend:**
```bash
docker-compose logs -f --tail=0 backend-openmedlab | grep -E "POST /api/dicom-gateway/transactions|201"
```

### Step 3: Verify Data Flow

After sending, run:
```bash
# Wait 30 seconds for processing, then check:
docker exec backend-openmedlab python -c "
import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings');
import django; django.setup();
from dicom_gateway.models import DICOMTransaction;
count = DICOMTransaction.objects.count();
print(f'✅ Transactions: {count}' if count > 0 else '❌ No transactions created')
"
```

### Step 4: Check Monitor Page

1. Open browser: `http://localhost:3000/monitor`
2. Click "Transfers" tab
3. Should see new transfer within 10 seconds (polling interval)

---

## Troubleshooting Commands

### If no transactions are created:

**Check Celery can reach backend:**
```bash
docker exec gateway-celery-worker curl -I http://backend-openmedlab:3080/api/dicom-gateway/transactions/
```
Expected: `HTTP/1.1 200 OK` or `401 Unauthorized` (both mean endpoint exists)

**Check Redis queue:**
```bash
docker exec redis-openmedlab redis-cli LLEN dicom_processing
```
Expected: `(integer) 0` (queue empty, tasks processed)

**Check for errors:**
```bash
docker-compose logs gateway-celery-worker --tail=100 | grep -i error
```

### If monitor page shows no data:

**Test API directly:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:3080/api/dicom-gateway/transfers/monitor/?scope=own&page_size=20"
```

**Check frontend polling:**
- Open browser DevTools (F12)
- Network tab
- Filter by "monitor"
- Should see requests every 10 seconds

---

## Success Criteria

✅ **Gateway receives:** C-STORE logs appear
✅ **Files saved:** *.dcm files in /app/storage
✅ **Tasks queued:** Celery log shows "received"
✅ **Tasks processed:** Celery log shows "succeeded"
✅ **Transactions created:** Database count > 0
✅ **API returns data:** /monitor/ endpoint returns results
✅ **Frontend displays:** Monitor page shows transfers

---

## Quick One-Liner Test

After sending from Orthanc, wait 30 seconds then run:
```bash
docker exec backend-openmedlab python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings'); import django; django.setup(); from dicom_gateway.models import DICOMTransaction; print('✅ SUCCESS!' if DICOMTransaction.objects.count() > 0 else '❌ FAILED - No transactions')"
```
