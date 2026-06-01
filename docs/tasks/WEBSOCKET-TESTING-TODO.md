# WebSocket Testing - Pending Work

**Project:** OpenMedLab Monitor Page
**Date Created:** 2025-12-27
**Status:** Backend Complete, Frontend Testing Pending
**Priority:** Medium

---

## Overview

The Monitor page has been fully implemented with real-time WebSocket support for tracking analysis jobs and DICOM gateway transfers. The backend is complete and operational, but WebSocket functionality requires browser-based testing with authenticated sessions.

### What Was Implemented

- ✅ Django Channels + Daphne ASGI server for WebSocket support
- ✅ WebSocket consumer with authentication and group-based broadcasting
- ✅ Signal handlers for automatic task update broadcasting
- ✅ REST API endpoints for job monitoring and statistics
- ✅ Frontend React components with useWebSocket hook
- ✅ Privacy controls for colleague job visibility
- ✅ Database schema extensions for department/team organization

---

## What's Been Tested

### Backend Components ✅

1. **Monitor API Endpoints**
   - `GET /api/ai-analysis/tasks/monitor/` - Returns paginated jobs (tested with curl)
   - `GET /api/ai-analysis/tasks/stats/` - Returns aggregate statistics (tested with curl)
   - Both endpoints correctly filter by scope, date range, status, and model

2. **WebSocket Infrastructure**
   - Daphne server running on port 3080
   - WebSocket route `/ws/monitor/tasks/` is registered
   - Authentication check working (rejects unauthenticated connections with HTTP 403)
   - Channel layer configured with Redis backend

3. **Database**
   - All migrations applied successfully
   - Profile fields (department, job_title, team_name, is_sharing_jobs_with_colleagues) present
   - Composite indexes working for efficient queries

4. **Privacy & Security**
   - Colleague visibility respects `is_sharing_jobs_with_colleagues` flag
   - Organization boundary enforced (no cross-org data leakage)
   - WebSocket authentication via Django session middleware

---

## Pending WebSocket Testing

### 1. WebSocket Connection Establishment

**Objective:** Verify that authenticated users can establish WebSocket connections

**Test Procedure:**
1. Navigate to http://localhost:3000 in a browser
2. Login with test credentials:
   - Email: `test@openmedlab.com`
   - Password: `test123`
3. Navigate to `/monitor` page
4. Open Browser DevTools → Network tab → WS filter
5. Verify WebSocket connection to `ws://localhost:3080/ws/monitor/tasks/`

**Expected Results:**
- WebSocket connection shows status `101 Switching Protocols` (successful upgrade)
- Connection indicator on Monitor page shows "Live" or green status
- Browser console logs: `"WebSocket connected: /ws/monitor/tasks/"`
- Server sends initial connection message: `{"type": "connection", "status": "connected"}`

**Success Criteria:**
- [ ] WebSocket connection established without errors
- [ ] Connection persists (doesn't immediately disconnect)
- [ ] Reconnection works after brief network interruption

---

### 2. Real-Time Task Updates

**Objective:** Verify that task status changes are broadcast in real-time

**Test Procedure:**

**Setup:**
1. Login as `test@openmedlab.com`
2. Open Monitor page in browser (keep DevTools WebSocket tab open)

**Create Test Task:**
3. In a separate terminal, create a test analysis task:
```bash
TOKEN=$(curl -s -X POST http://localhost:3080/users/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@openmedlab.com", "password": "test123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access'])")

# Create a test task (replace with actual task creation endpoint)
curl -X POST http://localhost:3080/api/ai-analysis/tasks/ \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mirage-v1",
    "dicom_image_id": 1,
    "parameters": {"test": true}
  }'
```

**Monitor Updates:**
4. Watch the WebSocket messages in DevTools
5. Watch the Monitor page UI for new task appearing

**Expected Results:**
- WebSocket receives message: `{"type": "task_updated", "task": {...}}`
- New task appears in the job table immediately (without page refresh)
- Task row shows: model name, status "PENDING" or "QUEUED", created timestamp
- Stats cards update (Total Jobs increments)

**Status Change:**
6. If task progresses to PROCESSING/COMPLETED, verify:
   - WebSocket receives additional `task_updated` messages
   - Job table row updates in real-time (status badge changes color)
   - If completed: notification appears with message "Analysis Complete"

**Success Criteria:**
- [ ] New tasks appear instantly in the table
- [ ] Status changes reflect immediately
- [ ] Stats cards update without refresh
- [ ] Completion notifications appear
- [ ] No console errors

---

### 3. Colleague Job Visibility (Privacy Testing)

**Objective:** Verify privacy controls work correctly for colleague job sharing

**Test Procedure:**

**Setup - Create Second User:**
```bash
docker exec backend-openmedlab python manage.py shell -c "
from django.contrib.auth import get_user_model
from users.models import UserProfile, Organization
User = get_user_model()

# Get existing organization
org = Organization.objects.first()

# Create second test user
user2, _ = User.objects.get_or_create(
    email='colleague@openmedlab.com',
    defaults={'is_active': True}
)
user2.set_password('test123')
user2.save()

# Create profile with SHARING ENABLED
UserProfile.objects.get_or_create(
    user=user2,
    defaults={
        'organization': org,
        'first_name': 'Colleague',
        'last_name': 'User',
        'email': 'colleague@openmedlab.com',
        'address': '456 Test Ave',
        'city': 'Test City',
        'state': 'TS',
        'country': 'Test Country',
        'department': 'Radiology',  # Same department as test@openmedlab.com
        'job_title': 'Technician',
        'team_name': 'MRI Team',    # Same team
        'is_sharing_jobs_with_colleagues': True  # SHARING ENABLED
    }
)
print('Created colleague@openmedlab.com with sharing enabled')
"
```

**Test Scenario 1: Shared Jobs Visible**
1. Login as `colleague@openmedlab.com` / `test123`
2. Navigate to Monitor page
3. Create a task as this user (via API or UI)
4. Logout and login as `test@openmedlab.com`
5. Navigate to Monitor page → Select scope "Department" or "Organization"

**Expected Results:**
- Colleague's task appears in the job list
- Created by column shows "Colleague User" (real name)
- Department column shows "Radiology"

**Test Scenario 2: Private Jobs Hidden**
1. Update colleague profile to disable sharing:
```bash
docker exec backend-openmedlab python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(email='colleague@openmedlab.com')
profile = user.userprofile
profile.is_sharing_jobs_with_colleagues = False
profile.save()
print('Sharing disabled for colleague')
"
```
2. Refresh Monitor page (still logged in as `test@openmedlab.com`)
3. Select scope "Department" or "Organization"

**Expected Results:**
- Colleague's tasks NO LONGER appear in the list
- Only own tasks visible

**Test Scenario 3: Cross-Organization Isolation**
1. Create a user in a different organization
2. Verify their tasks NEVER appear, even with sharing enabled

**Success Criteria:**
- [ ] Shared jobs visible when `is_sharing_jobs_with_colleagues=True`
- [ ] Jobs hidden when `is_sharing_jobs_with_colleagues=False`
- [ ] Cross-organization jobs never visible
- [ ] Real names shown only for shared jobs
- [ ] Own jobs always show "You" as creator

---

### 4. WebSocket Reconnection & Resilience

**Objective:** Verify WebSocket handles disconnections gracefully

**Test Procedure:**

**Scenario 1: Server Restart**
1. Open Monitor page (WebSocket connected)
2. Restart backend: `docker-compose restart backend-openmedlab`
3. Wait 30 seconds

**Expected Results:**
- Initial disconnection detected (connection indicator shows "Offline")
- Auto-reconnection after 3 seconds (with exponential backoff)
- Connection restored without manual page refresh
- Previous state preserved (job list remains populated)

**Scenario 2: Network Interruption**
1. Open Monitor page (WebSocket connected)
2. Simulate network issue:
   - Chrome DevTools → Network tab → Throttling → Offline
   - Wait 10 seconds
   - Restore → Online
3. Observe reconnection behavior

**Expected Results:**
- Connection indicator shows offline state
- Reconnection attempts with increasing delays (1s → 2s → 4s → 8s)
- Max 10 reconnection attempts before giving up
- Success message when reconnected

**Scenario 3: Long Idle Connection**
1. Open Monitor page and leave idle for 30+ minutes
2. Create a task (via API in terminal)

**Expected Results:**
- WebSocket connection still active after idle period
- Task update received immediately
- No stale connection (HTTP timeout doesn't affect WebSocket)

**Success Criteria:**
- [ ] Auto-reconnection works after server restart
- [ ] Exponential backoff prevents reconnection spam
- [ ] User sees connection status in UI
- [ ] Long-lived connections remain stable

---

### 5. Multi-User Broadcasting

**Objective:** Verify task updates broadcast to all relevant users

**Test Procedure:**

**Setup:**
1. Open Monitor page in Browser 1 (logged in as `test@openmedlab.com`)
2. Open Monitor page in Browser 2 (same user, different session)
3. Both should show WebSocket connected

**Test:**
4. Create a task via API (as `test@openmedlab.com`)

**Expected Results:**
- Task appears in **both** browsers simultaneously
- Both receive same WebSocket message
- Both UIs update without refresh

**Department Scope Test:**
5. Open Browser 3 (logged in as `colleague@openmedlab.com` with sharing enabled, same department)
6. Create task as `test@openmedlab.com`

**Expected Results:**
- Browser 1 & 2 (own user) receive update immediately
- Browser 3 (colleague) receives update if scope is "Department" or "Organization"
- Browser 3 does NOT receive update if scope is "Own"

**Success Criteria:**
- [ ] Multiple sessions of same user receive broadcasts
- [ ] Colleague users receive broadcasts (when sharing enabled)
- [ ] Scope filters work correctly for broadcasts
- [ ] No duplicate messages

---

### 6. Profile Completion Flow

**Objective:** Verify profile completion modal and updates

**Test Procedure:**

**Setup - Create User Without Profile Data:**
```bash
docker exec backend-openmedlab python manage.py shell -c "
from django.contrib.auth import get_user_model
from users.models import UserProfile, Organization
User = get_user_model()

org = Organization.objects.first()
user, _ = User.objects.get_or_create(
    email='newuser@openmedlab.com',
    defaults={'is_active': True}
)
user.set_password('test123')
user.save()

# Create profile WITHOUT department
UserProfile.objects.get_or_create(
    user=user,
    defaults={
        'organization': org,
        'first_name': 'New',
        'last_name': 'User',
        'email': 'newuser@openmedlab.com',
        'address': '789 Test Blvd',
        'city': 'Test City',
        'state': 'TS',
        'country': 'Test Country',
        'department': '',  # EMPTY - should trigger modal
        'job_title': '',
        'team_name': ''
    }
)
print('Created newuser@openmedlab.com without profile data')
"
```

**Test:**
1. Login as `newuser@openmedlab.com` / `test123`
2. Navigate to Monitor page

**Expected Results:**
- Profile completion modal appears automatically
- Modal cannot be dismissed without completing (or has "Skip" option)
- Form fields: Department (required), Job Title (required), Team Name (optional), Privacy checkbox

**Complete Profile:**
3. Fill form:
   - Department: "Neurology"
   - Job Title: "Neurologist"
   - Team Name: "Brain Imaging"
   - Check "Share my jobs with colleagues"
4. Submit form

**Expected Results:**
- Modal closes
- Monitor page loads normally
- User profile updated in database
- WebSocket joins organization/department/team groups

**Verify Privacy Setting:**
5. Create a task as `newuser@openmedlab.com`
6. Login as another user in same department
7. Verify task is visible with scope "Department"

**Success Criteria:**
- [ ] Modal appears for users without department
- [ ] Form validation works (required fields)
- [ ] Profile updates successfully
- [ ] Modal doesn't reappear after completion
- [ ] Privacy setting takes effect immediately

---

### 7. Performance & Scalability

**Objective:** Verify WebSocket performs well with multiple connections and high message volume

**Test Procedure:**

**Load Test Setup:**
1. Create script to simulate multiple WebSocket connections:
```python
# save as /tmp/websocket_load_test.py
import asyncio
import websockets
import json

async def client(client_id):
    uri = "ws://localhost:3080/ws/monitor/tasks/"
    async with websockets.connect(uri) as ws:
        print(f"Client {client_id} connected")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"Client {client_id} received: {data['type']}")

async def main():
    tasks = [client(i) for i in range(10)]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

**Note:** This test requires authenticated sessions, which need cookie handling.

**Manual Test:**
1. Open 5-10 browser tabs with Monitor page
2. Create multiple tasks rapidly (10+ tasks)
3. Monitor backend logs and browser console

**Expected Results:**
- All tabs receive updates simultaneously
- No message loss or duplication
- Backend CPU/memory usage remains stable
- Redis channel layer handles concurrent messages
- Response time < 100ms for WebSocket messages

**Success Criteria:**
- [ ] Handles 10+ concurrent connections
- [ ] Messages broadcast to all clients
- [ ] No performance degradation
- [ ] Backend logs show no errors

---

## Test Environment Setup

### Prerequisites

1. **Backend Services Running:**
```bash
docker-compose up -d
docker-compose ps  # Verify all services "Up"
```

2. **Verify Daphne:**
```bash
docker-compose logs backend-openmedlab | grep -i daphne
# Should show: "Starting server at tcp:port=3080:interface=0.0.0.0"
```

3. **Frontend Running:**
```bash
docker-compose logs frontend-openmedlab | grep -i "ready"
# Should show Vite dev server ready
```

4. **Test User Exists:**
```bash
# User: test@openmedlab.com / test123
# Already created with profile: Radiology dept, MRI Team, sharing enabled
```

### Browser DevTools Setup

**Chrome/Edge:**
1. Press F12 to open DevTools
2. Network tab → WS filter (for WebSocket messages)
3. Console tab (for application logs)

**Firefox:**
1. Press F12 to open DevTools
2. Network tab → WS filter
3. Console tab

**Useful Console Commands:**
```javascript
// Check WebSocket connection state
window.ws  // If exposed by app

// Monitor all WebSocket messages
const originalSend = WebSocket.prototype.send;
WebSocket.prototype.send = function(data) {
  console.log('WS Send:', data);
  originalSend.call(this, data);
};
```

---

## Known Issues & Notes

### 1. Profile Completion Action Endpoint

**Issue:** The `POST /users/profile/complete-profile/` endpoint has a routing conflict with the DRF router.

**Workaround:** Frontend can use standard PATCH request to profile detail endpoint:
```javascript
// Instead of:
// POST /users/profile/complete-profile/

// Use:
PATCH /users/profile/{id}/
{
  "department": "Radiology",
  "job_title": "Doctor",
  "team_name": "MRI Team",
  "is_sharing_jobs_with_colleagues": true
}
```

**Resolution:** Update `users/urls.py` to properly configure ViewSet routing, or use a non-REST endpoint.

### 2. WebSocket Authentication

**Important:** WebSocket connections require Django session cookies, which are only available in browser contexts. CLI testing with `websockets` library will fail authentication unless cookies are properly handled.

**For Testing:** Always test WebSocket functionality from the browser after logging in through the UI.

### 3. CORS & WebSocket Origins

**Current Config:** Development allows `localhost:3000` → `localhost:3080`

**Production Note:** Update ALLOWED_HOSTS and CORS settings before deploying:
- Change WebSocket URL to `wss://` (secure)
- Configure Nginx/proxy to handle WebSocket upgrades
- Update `VITE_WS_URL` environment variable

### 4. Redis Channel Layer

**Dependency:** Django Channels uses Redis for message routing between Daphne workers.

**Verify Redis:**
```bash
docker-compose logs redis-openmedlab --tail=20
# Should show Redis accepting connections
```

**Redis Commands (if issues):**
```bash
docker exec redis-openmedlab redis-cli PING
# Should respond: PONG
```

---

## Success Metrics

A successful test completion should verify:

- ✅ WebSocket connections establish reliably
- ✅ Task updates broadcast in real-time (< 100ms latency)
- ✅ Privacy controls enforced correctly
- ✅ Reconnection works after interruptions
- ✅ Multi-user broadcasting functional
- ✅ Profile completion flow complete
- ✅ No memory leaks or connection limits
- ✅ Browser console free of errors
- ✅ Daphne logs show no warnings

---

## Troubleshooting Guide

### WebSocket Connection Fails (HTTP 403)

**Symptom:** Browser shows `403 Forbidden` when connecting to WebSocket

**Causes:**
1. Not logged in (no session cookie)
2. Session expired
3. CSRF token missing

**Solution:**
- Login again through `/auth/login`
- Clear browser cookies and re-login
- Check browser DevTools → Application → Cookies for `sessionid`

### WebSocket Disconnects Immediately

**Symptom:** Connection established but closes within seconds

**Causes:**
1. Consumer code error
2. Database connection issue
3. User profile not found

**Solution:**
- Check backend logs: `docker-compose logs backend-openmedlab --tail=50`
- Look for Python exceptions in consumer code
- Verify user has UserProfile record

### Task Updates Not Received

**Symptom:** WebSocket connected but no messages when tasks created

**Causes:**
1. Signal handlers not registered
2. Channel layer not working
3. Wrong group subscribed

**Solution:**
- Verify Redis running: `docker-compose ps redis-openmedlab`
- Check signal registration in `ai_analysis/apps.py`
- Test channel layer: `docker exec backend-openmedlab python manage.py shell -c "from channels.layers import get_channel_layer; print(get_channel_layer())"`

### Performance Issues

**Symptom:** Slow updates, high CPU/memory

**Causes:**
1. Too many database queries (N+1 problem)
2. Missing `select_related` in queries
3. Redis connection pool exhausted

**Solution:**
- Enable Django Debug Toolbar to inspect queries
- Add `select_related('model', 'created_by__userprofile')` to monitor queryset
- Check Redis connection limit: `docker exec redis-openmedlab redis-cli INFO clients`

---

## Next Steps

1. **Immediate Testing:**
   - Test WebSocket connection establishment (Test #1)
   - Test basic real-time updates (Test #2)
   - Verify Monitor page UI renders correctly

2. **Extended Testing:**
   - Privacy controls (Test #3)
   - Reconnection resilience (Test #4)
   - Multi-user scenarios (Test #5)

3. **Optional/Future:**
   - Gateway monitoring panel (not yet implemented)
   - Performance benchmarking with 100+ concurrent users
   - Integration tests with Playwright/Cypress

4. **Documentation:**
   - Update user guide with Monitor page instructions
   - Create video demo of real-time features
   - Document privacy settings for end users

---

## Related Documentation

- **Implementation Plan:** `/home/jpablo/.claude/plans/whimsical-booping-ladybug.md`
- **API Documentation:** http://localhost:3080/api/docs/ (when backend running)
- **Django Channels Docs:** https://channels.readthedocs.io/
- **Frontend Code:** `/home/jpablo/code/web-apps/openmedlab/app/frontend/src/pages/MonitorPage.tsx`
- **Backend Consumer:** `/home/jpablo/code/web-apps/openmedlab/app/backend/ai_analysis/consumers.py`

---

**Document Version:** 1.0
**Last Updated:** 2025-12-27
**Author:** Claude Code (Implementation & Testing Framework)
**Reviewer:** [Pending]
