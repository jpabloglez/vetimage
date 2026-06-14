# DICOM Transfer Monitoring Guide

## Overview

This guide provides comprehensive instructions for monitoring and verifying the DICOM transfer workflow in OpenMedLab. It covers system health checks, real-time monitoring, troubleshooting, and performance optimization.

## Table of Contents

1. [Quick Health Check](#quick-health-check)
2. [Complete Workflow Testing](#complete-workflow-testing)
3. [Real-Time Monitoring](#real-time-monitoring)
4. [Component-Level Monitoring](#component-level-monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Performance Monitoring](#performance-monitoring)
7. [Dashboard Usage](#dashboard-usage)

---

## Quick Health Check

### 1. Check All Services Running

```bash
docker-compose ps
```

**Expected Output:**
```
NAME                    STATUS
backend-openmedlab      Up
db                      Up
frontend-openmedlab     Up
gateway-api             Up
gateway-celery-worker   Up
gateway-scp             Up
redis                   Up
```

### 2. Verify Gateway Listening

```bash
docker-compose logs gateway-scp | grep "DICOM SCP started"
```

**Expected:** `DICOM SCP started on 0.0.0.0:11112 (AE Title: OPENMEDLAB)`

### 3. Check Celery Worker Status

```bash
docker-compose logs gateway-celery-worker | grep "ready"
```

**Expected:** `[2024-XX-XX] [INFO/MainProcess] celery@xxx ready.`

### 4. Test Backend API Health

```bash
curl -s http://localhost:8000/api/dicom-gateway/transactions/ | head -n 20
```

**Expected:** JSON response (even if empty)

---

## Complete Workflow Testing

### Step 1: Prepare Test Environment

```bash
# Clear previous test data (optional)
docker exec backend-openmedlab python manage.py shell -c "
from dicom_gateway.models import DICOMTransaction
DICOMTransaction.objects.all().delete()
print('Cleared all transactions')
"
```

### Step 2: Send Test DICOM Study

**From Orthanc (http://localhost:8042):**

1. Upload a DICOM study to Orthanc
2. Navigate to the study
3. Click "Send to DICOM modality"
4. Select or add destination:
   - **AE Title:** `OPENMEDLAB`
   - **Host:** `host.docker.internal` (or your machine IP)
   - **Port:** `11112`
5. Click "Send"

### Step 3: Monitor Gateway Reception (30 seconds)

```bash
# Watch gateway logs in real-time
docker-compose logs -f gateway-scp
```

**Expected Output:**
```
Received C-STORE request
Successfully stored: /app/storage/dicom-temp/[study]/[series]/[instance].dcm
```

**Stop watching:** Press `Ctrl+C` after seeing confirmations

### Step 4: Monitor Celery Processing (30 seconds)

```bash
# Watch Celery worker processing
docker-compose logs -f gateway-celery-worker
```

**Expected Output (for each instance):**
```
[INFO] Task gateway.tasks.process_dicom_file[xxx] received
[INFO] Processing DICOM file: /app/storage/dicom-temp/...
[INFO] DICOM file validated: 1.2.840...
[INFO] Uploaded to backend: {'uploaded_images': [{'id': 123, ...}]}
[INFO] Transaction logged to backend
[INFO] Task gateway.tasks.process_dicom_file[xxx] succeeded in 2.5s
```

**Stop watching:** Press `Ctrl+C` after all instances processed

### Step 5: Verify Database Records

```bash
# Check transactions created
docker exec backend-openmedlab python -c "
from dicom_gateway.models import DICOMTransaction
from django.db.models import Count

total = DICOMTransaction.objects.count()
by_study = DICOMTransaction.objects.values('study_instance_uid').annotate(count=Count('id'))

print(f'Total transactions: {total}')
print(f'Unique studies: {by_study.count()}')
print('\nRecent transactions:')
for t in DICOMTransaction.objects.order_by('-started_at')[:5]:
    print(f'  {t.started_at.strftime(\"%H:%M:%S\")} | {t.modality or \"?\"} | {t.status} | {t.source_ae}')
"
```

**Expected:** Transactions matching the number of instances sent

### Step 6: Verify Monitor API Response

```bash
# Test monitor endpoint
curl -s "http://localhost:8000/api/dicom-gateway/transfers/monitor/?scope=own" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" | python3 -m json.tool | head -n 50
```

**Expected:** Study-level aggregated data with transfer metrics

### Step 7: Check Frontend Display

1. Open browser: http://localhost:3000
2. Navigate to **Monitor** page
3. Within **10 seconds**, you should see:
   - New study in transfer list
   - Updated statistics cards
   - Transfer status (success/in_progress)

---

## Real-Time Monitoring

### Monitor All Components Simultaneously

**Terminal 1: Gateway Reception**
```bash
docker-compose logs -f gateway-scp | grep -E "C-STORE|stored"
```

**Terminal 2: Celery Processing**
```bash
docker-compose logs -f gateway-celery-worker | grep -E "Processing|Uploaded|Transaction logged|succeeded|failed"
```

**Terminal 3: Backend Logs**
```bash
docker-compose logs -f backend-openmedlab | grep -E "POST|dicom-gateway|error"
```

**Terminal 4: Database Watch**
```bash
watch -n 5 'docker exec backend-openmedlab python -c "
from dicom_gateway.models import DICOMTransaction
print(f\"Transactions: {DICOMTransaction.objects.count()}\")
print(f\"Success: {DICOMTransaction.objects.filter(status=\"success\").count()}\")
print(f\"Failed: {DICOMTransaction.objects.filter(status=\"failure\").count()}\")
print(f\"Pending: {DICOMTransaction.objects.filter(status=\"pending\").count()}\")
"'
```

---

## Component-Level Monitoring

### Gateway SCP (DICOM Receiver)

**Check listening status:**
```bash
docker-compose logs gateway-scp | tail -n 50
```

**Monitor incoming connections:**
```bash
docker-compose logs -f gateway-scp | grep "Association"
```

**Check storage path:**
```bash
docker exec gateway-scp ls -lh /app/storage/dicom-temp/
```

### Celery Worker (Task Processor)

**Check worker health:**
```bash
docker exec gateway-celery-worker celery -A gateway.tasks inspect active
```

**View active tasks:**
```bash
docker exec gateway-celery-worker celery -A gateway.tasks inspect active
```

**View registered tasks:**
```bash
docker exec gateway-celery-worker celery -A gateway.tasks inspect registered
```

**Check queue length:**
```bash
docker exec redis redis-cli llen dicom_processing
```

**Expected:** `0` when idle, increases temporarily when processing

### Backend API (Django)

**Check recent API calls:**
```bash
docker-compose logs backend-openmedlab | grep "POST.*dicom-gateway" | tail -n 20
```

**Test transaction creation endpoint:**
```bash
curl -X POST http://localhost:8000/api/dicom-gateway/transactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_type": "C-STORE",
    "direction": "incoming",
    "source_ae": "TEST",
    "source_ip": "127.0.0.1",
    "dest_ae": "OPENMEDLAB",
    "study_instance_uid": "1.2.3.4.5.6.7.8.9",
    "series_instance_uid": "1.2.3.4.5.6.7.8.9.1",
    "sop_instance_uid": "1.2.3.4.5.6.7.8.9.1.1",
    "status": "success",
    "started_at": "2024-01-01T12:00:00Z"
  }'
```

**Expected:** `201 Created` with transaction ID

### Database (PostgreSQL)

**Connect to database:**
```bash
docker exec -it db psql -U openmedlab -d openmedlab
```

**Check transaction table:**
```sql
SELECT COUNT(*) as total,
       status,
       transaction_type,
       direction
FROM dicom_gateway_dicomtransaction
GROUP BY status, transaction_type, direction;

\q
```

**Recent transactions:**
```bash
docker exec db psql -U openmedlab -d openmedlab -c "
SELECT
    id,
    TO_CHAR(started_at, 'HH24:MI:SS') as time,
    modality,
    status,
    source_ae
FROM dicom_gateway_dicomtransaction
ORDER BY started_at DESC
LIMIT 10;
"
```

---

## Troubleshooting

### Issue: No Transactions Created

**Symptoms:** Gateway receives files but database remains empty

**Diagnosis:**
```bash
# 1. Check Celery is processing tasks
docker-compose logs gateway-celery-worker | grep "process_dicom_file"

# 2. Check for errors in Celery logs
docker-compose logs gateway-celery-worker | grep -i error

# 3. Verify queue routing
docker exec gateway-celery-worker celery -A gateway.tasks inspect active_queues
```

**Expected queue:** `dicom_processing`

**Solution:**
- If queue mismatch: Check `gateway/tasks.py` line 37 (task_default_queue)
- If authentication errors: Verify gateway service user exists
- If validation errors: Check serializer field configuration

### Issue: Transactions Created But Not Appearing in Monitor

**Symptoms:** Database has records but frontend shows empty

**Diagnosis:**
```bash
# 1. Check API endpoint directly
curl -s "http://localhost:8000/api/dicom-gateway/transfers/monitor/?scope=own" \
  -H "Authorization: Bearer YOUR_TOKEN" | python3 -m json.tool

# 2. Check frontend polling is active
# Open browser console, look for:
#   [useMonitoring] Fetching monitor data...
#   [useMonitoring] Monitor data updated: {...}

# 3. Verify user authentication
# Look for 401 errors in browser console
```

**Solutions:**
- If 401 errors: Refresh browser or re-login
- If empty response: Check organization/scope filtering
- If polling not active: Verify config endpoint returns correct intervals

### Issue: Transfers Show "In Progress" Forever

**Symptoms:** Transfers stuck in pending status

**Diagnosis:**
```bash
# Check for pending transactions
docker exec backend-openmedlab python -c "
from dicom_gateway.models import DICOMTransaction
pending = DICOMTransaction.objects.filter(status='pending')
print(f'Pending transactions: {pending.count()}')
for t in pending[:5]:
    print(f'  {t.sop_instance_uid} - {t.started_at}')
"

# Check Celery for stalled tasks
docker exec gateway-celery-worker celery -A gateway.tasks inspect active
```

**Solutions:**
- If tasks stalled: Restart Celery worker
- If tasks missing: Check queue routing
- If database not updated: Check for errors in Celery logs

### Issue: High Error Rate

**Symptoms:** Many transactions with status='failure'

**Diagnosis:**
```bash
# Get error messages
docker exec backend-openmedlab python -c "
from dicom_gateway.models import DICOMTransaction
failed = DICOMTransaction.objects.filter(status='failure')
print(f'Failed transactions: {failed.count()}')
print('\nRecent errors:')
for t in failed.order_by('-started_at')[:10]:
    print(f'{t.error_message}')
" | sort | uniq -c | sort -rn
```

**Common errors:**
- `Failed to get auth token`: Gateway service user credentials incorrect
- `Backend upload failed: HTTP 400`: File validation issue
- `DICOM file not found`: Storage path or permissions issue

---

## Performance Monitoring

### Transfer Speed Metrics

```bash
# Average transfer time and throughput
docker exec backend-openmedlab python -c "
from dicom_gateway.models import DICOMTransaction
from django.db.models import Avg, Sum, Count
from datetime import timedelta
from django.utils import timezone

last_hour = timezone.now() - timedelta(hours=1)

stats = DICOMTransaction.objects.filter(
    started_at__gte=last_hour,
    status='success'
).aggregate(
    avg_duration_ms=Avg('duration_ms'),
    total_bytes=Sum('file_size_bytes'),
    total_count=Count('id')
)

if stats['avg_duration_ms']:
    print(f\"Last Hour Performance:\")
    print(f\"  Transfers: {stats['total_count']}\")
    print(f\"  Avg Duration: {stats['avg_duration_ms']:.0f} ms\")
    print(f\"  Total Data: {stats['total_bytes'] / (1024**2):.1f} MB\")
    print(f\"  Throughput: {(stats['total_bytes'] / (1024**2)) / (stats['avg_duration_ms'] / 1000):.2f} MB/s\")
else:
    print('No transfers in last hour')
"
```

### Queue Monitoring

```bash
# Check queue depth over time
for i in {1..10}; do
  echo -n "$(date +%H:%M:%S) - Queue: "
  docker exec redis redis-cli llen dicom_processing
  sleep 5
done
```

**Healthy:** Queue stays at 0 or processes quickly
**Warning:** Queue depth > 100 indicates backlog

### Resource Usage

```bash
# Container resource usage
docker stats --no-stream backend-openmedlab gateway-celery-worker gateway-scp

# Disk usage for DICOM storage
docker exec gateway-scp du -sh /app/storage/dicom-temp/

# Database size
docker exec db psql -U openmedlab -d openmedlab -c "
SELECT
    pg_size_pretty(pg_total_relation_size('dicom_gateway_dicomtransaction')) as transaction_table_size,
    COUNT(*) as row_count
FROM dicom_gateway_dicomtransaction;
"
```

---

## Dashboard Usage

### Monitor Page Features

**Location:** http://localhost:3000/monitor

**Components:**

1. **Statistics Cards** (Top Row)
   - Total Transfers (24h)
   - Success Rate (%)
   - Avg Transfer Time (seconds)
   - Total Data Received (MB)
   - Updates every **30 seconds** (polling mode)

2. **Transfer List** (Main Panel)
   - Study-level aggregation
   - Shows: Study date, description, modality, instances, status
   - Updates every **10 seconds** (polling mode)
   - Clickable rows for details

3. **Filters** (Sidebar)
   - Date range (default: last 24h)
   - Status: All, Success, Partial, Failed, In Progress
   - Source PACS
   - Modality
   - Scope: Own, Colleagues, Department, Team

4. **Settings** (Gear Icon)
   - View tracking mode (WebSocket/Polling)
   - View polling intervals
   - Manual refresh button

### Understanding Transfer Status

**Status Values:**
- **Success** 🟢: All instances transferred successfully
- **Partial** 🟡: Some instances failed, some succeeded
- **In Progress** 🔵: Transfer currently ongoing (pending instances)
- **Failed** 🔴: All instances failed

**Status Calculation:**
```
if pending_instances > 0:
    status = "in_progress"
elif failed_instances == total_instances:
    status = "failed"
elif failed_instances > 0:
    status = "partial"
else:
    status = "success"
```

### Polling Mode Indicator

In the top-right corner, you'll see:
- **WebSocket Mode:** Green/red dot (connection status)
- **Polling Mode:** Text showing "Polling (10s)" or "Polling (30s)"

**To change mode:** Edit `app/backend/.env`:
```bash
WEBSOCKET_BASED_TRACKING=False  # Polling (default, reliable)
WEBSOCKET_BASED_TRACKING=True   # WebSocket (real-time, requires stable connection)
```

Then restart backend:
```bash
docker-compose restart backend-openmedlab
```

---

## Automated Monitoring Script

Save this as `monitor-dicom.sh`:

```bash
#!/bin/bash
# Real-time DICOM transfer monitoring

echo "=== OpenMedLab DICOM Transfer Monitor ==="
echo ""

# Function to get transaction counts
get_stats() {
    docker exec backend-openmedlab python -c "
from dicom_gateway.models import DICOMTransaction
from datetime import timedelta
from django.utils import timezone

last_minute = timezone.now() - timedelta(minutes=1)
recent = DICOMTransaction.objects.filter(started_at__gte=last_minute)

print(f'{DICOMTransaction.objects.count()}|{recent.count()}|{DICOMTransaction.objects.filter(status=\"success\").count()}|{DICOMTransaction.objects.filter(status=\"failure\").count()}')
" 2>/dev/null
}

# Function to get queue depth
get_queue() {
    docker exec redis redis-cli llen dicom_processing 2>/dev/null
}

# Monitor loop
while true; do
    clear
    echo "=== OpenMedLab DICOM Transfer Monitor ==="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    stats=$(get_stats)
    queue=$(get_queue)

    IFS='|' read -r total recent success failed <<< "$stats"

    echo "📊 Transaction Statistics:"
    echo "  Total All-Time: $total"
    echo "  Last Minute: $recent"
    echo "  Success: $success"
    echo "  Failed: $failed"
    echo ""
    echo "📦 Queue Depth: $queue"
    echo ""
    echo "🔄 Press Ctrl+C to stop monitoring"

    sleep 5
done
```

Make executable and run:
```bash
chmod +x monitor-dicom.sh
./monitor-dicom.sh
```

---

## Configuration Reference

### Polling Intervals (Default)

**File:** `app/backend/.env`

```bash
# Polling mode (reliable, default)
WEBSOCKET_BASED_TRACKING=False

# Monitor polling (task/transfer lists)
MONITOR_POLL_INTERVAL=10  # seconds

# Stats polling (statistics cards)
STATS_POLL_INTERVAL=30    # seconds
```

**Recommendations:**
- **High-frequency monitoring:** 5-10 seconds
- **Standard monitoring:** 10-15 seconds
- **Low-bandwidth/background:** 30-60 seconds

### WebSocket Mode (Optional)

```bash
# Enable WebSocket real-time updates
WEBSOCKET_BASED_TRACKING=True
WEBSOCKET_HEARTBEAT_INTERVAL=30
```

**Trade-offs:**
- ✅ Instant updates (< 1 second)
- ⚠️ Requires stable connection
- ⚠️ More complex debugging

---

## Health Check Checklist

Run before reporting issues:

- [ ] All Docker containers running (`docker-compose ps`)
- [ ] Gateway listening on port 11112 (`docker-compose logs gateway-scp`)
- [ ] Celery worker active (`docker-compose logs gateway-celery-worker`)
- [ ] Redis accessible (`docker exec redis redis-cli ping`)
- [ ] Backend API responding (`curl http://localhost:8000/api/config/`)
- [ ] Database connection working (`docker exec db psql -U openmedlab -c "SELECT 1;"`)
- [ ] No errors in backend logs (`docker-compose logs backend-openmedlab | grep -i error`)
- [ ] Transaction endpoint accepting POSTs (test with curl)
- [ ] Frontend loading (`http://localhost:3000`)
- [ ] Browser console clear of errors (F12 → Console)

---

## Support

**Log Collection for Bug Reports:**

```bash
# Collect all relevant logs
mkdir -p ~/openmedlab-logs
docker-compose logs gateway-scp > ~/openmedlab-logs/gateway-scp.log 2>&1
docker-compose logs gateway-celery-worker > ~/openmedlab-logs/celery.log 2>&1
docker-compose logs backend-openmedlab > ~/openmedlab-logs/backend.log 2>&1
docker-compose logs redis > ~/openmedlab-logs/redis.log 2>&1

# Database state
docker exec backend-openmedlab python -c "
from dicom_gateway.models import DICOMTransaction
print(f'Total: {DICOMTransaction.objects.count()}')
" > ~/openmedlab-logs/db-state.txt 2>&1

echo "Logs collected in ~/openmedlab-logs/"
```

**Configuration Export:**

```bash
# Export current configuration
docker exec backend-openmedlab python manage.py shell -c "
from django.conf import settings
print('WEBSOCKET_BASED_TRACKING:', settings.WEBSOCKET_BASED_TRACKING)
print('MONITOR_POLL_INTERVAL:', settings.MONITOR_POLL_INTERVAL)
print('STATS_POLL_INTERVAL:', settings.STATS_POLL_INTERVAL)
"
```

---

**Last Updated:** 2026-01-06
**Version:** 1.0.0
**Applies To:** OpenMedLab DICOM Gateway with Polling-Based Monitoring
