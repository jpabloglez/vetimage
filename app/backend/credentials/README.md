# Credentials App - Enhanced Authentication System

Comprehensive authentication enhancement for VetImage with session tracking, audit trails, and enhanced API key management.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
- [Models](#models)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Security](#security)

---

## Overview

The `credentials` app enhances the existing JWT authentication (djangorestframework-simplejwt) with:

- **Session Tracking**: Automatic tracking of JWT and API key sessions with device fingerprinting
- **Audit Trails**: Immutable audit logs for all authentication events
- **API Key Scopes**: Granular permission control for API keys (e.g., `dicom:read`, `ai:submit`)
- **Rate Limiting**: Configurable per-minute/hour/day quotas for API keys
- **Security Features**: Brute force protection, concurrent session limits, IP change detection

### Integration Approach

- **Non-invasive**: Signal-based integration with existing simplejwt
- **Backward Compatible**: All existing APIs continue working unchanged
- **Feature Flags**: Gradual rollout with configurable feature flags

---

## Features

### 1. Session Tracking

Automatically tracks every JWT login/logout and API key usage:

- **Device Fingerprinting**: Browser, OS, device type from User-Agent
- **Network Info**: IP address, geolocation (country, city)
- **Lifecycle Tracking**: Created, last activity, expires, terminated timestamps
- **Security Monitoring**: Suspicious activity flagging, IP change detection

### 2. Audit Logging

Immutable audit trail for all authentication events:

- **20+ Event Types**: Login success/failure, logout, token refresh, password changes, scope violations, etc.
- **Tamper-Proof**: Cannot be modified or deleted after creation
- **Rich Context**: IP address, user agent, request path/method, metadata
- **Risk Scoring**: Automatic risk score (0-100) for suspicious events

### 3. API Key Scopes

Granular permission control for API keys:

- **Scope-Based Access**: Define allowed endpoints and HTTP methods
- **Categories**: DICOM, AI, Users, Admin
- **Example Scopes**:
  - `dicom:read` - Read-only DICOM access (GET only)
  - `dicom:write` - Full DICOM access (all HTTP methods)
  - `ai:submit` - Submit AI analysis jobs (POST to `/api/ai-analysis/submit/`)
  - `full_access` - Unrestricted access (default for existing keys)

### 4. Rate Limiting

Configurable rate limits per API key:

- **Per-Minute**: Default 60 req/min
- **Per-Hour**: Default 3600 req/hour
- **Per-Day**: Default 86400 req/day
- **Redis-Based**: Distributed counting for horizontal scaling
- **Grace Periods**: Progressive delays for exceeded limits

### 5. Security Features

- **Brute Force Protection**: Progressive exponential backoff after failed logins
- **Concurrent Session Limits**: Automatic termination of oldest sessions (default: 5 per user)
- **IP Change Detection**: Flag sessions when IP address changes
- **Suspicious Activity Flagging**: Automatic detection of anomalous behavior

---

## Architecture

### Signal-Based Integration

```
JWT Login
  ↓
OutstandingToken created ────→ Signal creates UserSession
  ↓                            ├─ Extract device info
  ↓                            ├─ Create AuditLog entry
  ↓                            └─ Check concurrent session limits
Token returned to client

JWT Logout
  ↓
BlacklistedToken created ────→ Signal terminates UserSession
  ↓                            └─ Create AuditLog entry
Session ended
```

### Data Models

```
UserSession (tracks JWT/API key sessions)
  ├─ outstanding_token (OneToOne → OutstandingToken)
  ├─ session_type ('jwt' or 'api_key')
  ├─ device_type, browser, OS (from User-Agent)
  └─ ip_address, location (from request)

AuditLog (immutable audit trail)
  ├─ user, event_type, timestamp
  ├─ ip_address, user_agent, request context
  └─ is_suspicious, risk_score

APIKeyScope (permission definitions)
  ├─ name ('dicom:read', 'ai:submit', etc.)
  ├─ allowed_endpoints (regex patterns)
  └─ allowed_methods (['GET', 'POST', etc.])

EnhancedAPIKey (extends UserAPIKey)
  ├─ api_key (OneToOne → UserAPIKey)
  ├─ scopes (ManyToMany → APIKeyScope)
  └─ rate_limit_per_minute/hour/day

APIKeyUsageLog (request-level tracking)
  ├─ api_key, timestamp, request_path
  ├─ response_status, response_time_ms
  └─ scope_matched, rate_limited
```

---

## API Endpoints

Base URL: `/api/credentials/`

### Session Management

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/sessions/` | GET | JWT | List user's active sessions |
| `/sessions/{id}/` | GET | JWT | Get session details |
| `/sessions/{id}/` | DELETE | JWT | Terminate a session |
| `/sessions/current/` | GET | JWT | Get current session info |

### Audit Logs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/audit-logs/` | GET | JWT | List user's audit logs |
| `/audit-logs/{id}/` | GET | JWT | Get audit log details |
| `/audit-logs/export/` | GET | Admin/Manager | Export to CSV (last 10,000) |

**Query Parameters:**
- `event_type` - Filter by event type (e.g., `login_success`)
- `suspicious_only=true` - Only suspicious events
- `start_date` - Filter from date (ISO 8601)
- `end_date` - Filter until date (ISO 8601)

### API Key Scopes (Admin Only)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/scopes/` | GET | Admin | List all scopes |
| `/scopes/` | POST | Admin | Create new scope |
| `/scopes/{id}/` | GET/PUT/DELETE | Admin | Manage scope |

### API Key Management

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api-keys/` | GET | JWT | List user's API keys |
| `/api-keys/{id}/` | GET | JWT/Owner | Get API key details |
| `/api-keys/{id}/` | PATCH | JWT/Owner | Update scopes/rate limits |
| `/api-keys/{id}/usage/` | GET | JWT/Owner | Get usage statistics |
| `/api-keys/{id}/usage-logs/` | GET | JWT/Owner | List last 100 requests |
| `/api-keys/{id}/reset-quota/` | POST | Admin | Reset rate limit counters |

**Usage Statistics Query Parameters:**
- `days=30` - Time range in days (default: 30)

---

## Models

### UserSession

Tracks active JWT/API key sessions.

**Fields:**
- `id` (UUID) - Primary key
- `user` (FK) - Session owner
- `outstanding_token` (OneToOne) - JWT correlation
- `session_type` - 'jwt' or 'api_key'
- `device_type`, `browser`, `browser_version`, `os`, `os_version` - Device fingerprint
- `ip_address`, `ip_country`, `ip_city` - Network info
- `created_at`, `last_activity_at`, `expires_at`, `terminated_at` - Lifecycle
- `is_active`, `termination_reason` - Status
- `is_suspicious`, `suspicious_reason` - Security flags

**Methods:**
- `is_valid()` - Check if session is currently active
- `terminate(reason)` - End session with reason
- `update_activity()` - Update last activity timestamp

### AuditLog

Immutable audit trail for authentication events.

**Fields:**
- `id` (BigAutoField) - Primary key
- `user` (FK, nullable) - User involved
- `username_attempted` - Email/username used (even if failed)
- `event_type` - Event type (20+ choices)
- `event_timestamp` - When event occurred
- `ip_address`, `user_agent`, `request_path`, `request_method` - Request context
- `session` (FK) - Associated session
- `metadata` (JSONField) - Additional event-specific data
- `is_suspicious`, `risk_score` (0-100) - Security assessment

**Event Types:**
- **Authentication**: `login_success`, `login_failed`, `logout`, `token_refresh`, `token_expired`
- **Password**: `password_change`, `password_reset_request`, `password_reset_complete`
- **API Keys**: `apikey_auth`, `apikey_created`, `apikey_revoked`, `apikey_expired`
- **Sessions**: `session_created`, `session_terminated`, `concurrent_session_limit`
- **Security**: `suspicious_activity`, `rate_limit_exceeded`, `invalid_token`, `scope_violation`

**Immutability:**
- `save()` raises exception if pk exists (cannot modify)
- `delete()` raises exception (cannot delete)

### APIKeyScope

Permission definitions for API keys.

**Fields:**
- `id` (AutoField) - Primary key
- `name` - Unique scope identifier (e.g., "dicom:read")
- `display_name` - Human-readable name
- `description` - What this scope allows
- `category` - 'dicom', 'ai', 'users', 'admin'
- `allowed_endpoints` (JSONField) - List of URL regex patterns
- `allowed_methods` (JSONField) - Allowed HTTP methods
- `is_active` - Enable/disable scope

**Methods:**
- `matches_request(path, method)` - Check if scope allows given request

### EnhancedAPIKey

Extends UserAPIKey with scopes and rate limiting.

**Fields:**
- `api_key` (OneToOne) - Primary key, links to UserAPIKey
- `scopes` (ManyToMany) - Permissions granted
- `rate_limit_per_minute`, `rate_limit_per_hour`, `rate_limit_per_day` - Quotas
- `current_minute_count`, `current_hour_count`, `current_day_count`, `quota_reset_at` - Tracking
- `total_requests`, `last_request_at` - Statistics

**Methods:**
- `has_scope(scope_name)` - Check if key has specific scope
- `can_access(path, method)` - Check if key can access endpoint
- `check_rate_limit()` - Returns (allowed: bool, reason: str)
- `increment_usage()` - Increment request counters
- `reset_quotas()` - Reset rate limit counters

### APIKeyUsageLog

Detailed request-level tracking for API keys.

**Fields:**
- `id` (BigAutoField) - Primary key
- `api_key` (FK) - Key that made request
- `timestamp` - Request time
- `request_path`, `request_method` - Endpoint accessed
- `response_status`, `response_time_ms` - Performance metrics
- `ip_address` - Client IP
- `request_size_bytes`, `response_size_bytes` - Bandwidth tracking
- `scope_matched` - Which scope was used
- `rate_limited` - Whether request was rate limited

---

## Usage Examples

### 1. List Active Sessions

```bash
curl -H "Authorization: Bearer <JWT_ACCESS_TOKEN>" \
  http://localhost:8000/api/credentials/sessions/
```

**Response:**
```json
{
  "count": 3,
  "results": [
    {
      "id": "a1b2c3d4-...",
      "session_type": "jwt",
      "device_type": "desktop",
      "browser": "Chrome 120",
      "os": "Windows 11",
      "ip_address": "203.0.113.42",
      "ip_country": "US",
      "ip_city": "San Francisco",
      "created_at": "2026-01-07T10:30:00Z",
      "last_activity_at": "2026-01-10T14:22:15Z",
      "is_active": true,
      "is_current": true
    }
  ]
}
```

### 2. Revoke a Session

```bash
curl -X DELETE \
  -H "Authorization: Bearer <JWT_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "manual"}' \
  http://localhost:8000/api/credentials/sessions/a1b2c3d4.../
```

### 3. View Audit Logs (Suspicious Only)

```bash
curl -H "Authorization: Bearer <JWT_ACCESS_TOKEN>" \
  "http://localhost:8000/api/credentials/audit-logs/?suspicious_only=true"
```

### 4. Assign Scope to API Key

```python
from credentials.services import assign_scope_to_api_key
from users.models import UserAPIKey

api_key = UserAPIKey.objects.get(key_prefix='oml_abcd')
assign_scope_to_api_key(api_key, 'dicom:read')
```

### 5. Update API Key Scopes (REST API)

```bash
curl -X PATCH \
  -H "Authorization: Bearer <JWT_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"scope_names": ["dicom:read", "ai:view"]}' \
  http://localhost:8000/api/credentials/api-keys/5/
```

### 6. View API Key Usage Statistics

```bash
curl -H "Authorization: Bearer <JWT_ACCESS_TOKEN>" \
  "http://localhost:8000/api/credentials/api-keys/5/usage/?days=7"
```

**Response:**
```json
{
  "api_key_id": 5,
  "key_prefix": "oml_abcd",
  "total_requests": 145230,
  "rate_limits": {
    "per_minute": 60,
    "per_hour": 3600,
    "per_day": 86400
  },
  "current_usage": {
    "minute": 12,
    "hour": 847,
    "day": 12450,
    "quota_reset_at": "2026-01-11T00:00:00Z"
  },
  "scopes": ["dicom:read", "ai:submit"],
  "usage_by_endpoint": [
    {"request_path": "/api/dicom/upload/medical/", "count": 8234, "avg_response_ms": 1250},
    {"request_path": "/api/ai-analysis/submit/", "count": 3421, "avg_response_ms": 450}
  ]
}
```

### 7. Using Decorators in Views

```python
from credentials.decorators import require_api_key_scope, enforce_api_key_rate_limit
from rest_framework.decorators import api_view

@api_view(['POST'])
@require_api_key_scope('dicom:write')
@enforce_api_key_rate_limit
def upload_dicom(request):
    # Only API keys with "dicom:write" scope can access this
    # Automatically rate limited
    ...
```

### 8. Export Audit Logs (Admin Only)

```bash
curl -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
  "http://localhost:8000/api/credentials/audit-logs/export/?start_date=2026-01-01"
```

---

## Configuration

### Django Settings

Add to `backend/settings.py`:

```python
# Credentials App Configuration
MAX_CONCURRENT_SESSIONS_PER_USER = 5
SESSION_ACTIVITY_TIMEOUT_MINUTES = 30

# Brute Force Protection
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_TIMEOUT_SECONDS = 900  # 15 minutes

# API Key Rate Limiting (defaults)
DEFAULT_API_KEY_RATE_LIMIT_PER_MINUTE = 60
DEFAULT_API_KEY_RATE_LIMIT_PER_HOUR = 3600
DEFAULT_API_KEY_RATE_LIMIT_PER_DAY = 86400

# Feature Flags
CREDENTIALS_TRACKING_ENABLED = True
CREDENTIALS_AUDIT_LOGGING_ENABLED = True
CREDENTIALS_RATE_LIMITING_ENABLED = False  # Enable gradually

# GeoIP (optional)
GEOIP_DATABASE_PATH = '/app/geoip/GeoLite2-City.mmdb'

# Audit Log Retention
AUDIT_LOG_RETENTION_DAYS = 365
```

### Environment Variables

```bash
# Session Limits
MAX_CONCURRENT_SESSIONS_PER_USER=5
SESSION_ACTIVITY_TIMEOUT_MINUTES=30

# Brute Force Protection
MAX_LOGIN_ATTEMPTS=5
LOGIN_ATTEMPT_TIMEOUT_SECONDS=900

# Feature Flags
CREDENTIALS_TRACKING_ENABLED=True
CREDENTIALS_AUDIT_LOGGING_ENABLED=True
CREDENTIALS_RATE_LIMITING_ENABLED=False
```

### Redis Configuration

Required for rate limiting and brute force protection:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis-vetimage:6379/1',
        'KEY_PREFIX': 'vetimage',
        'TIMEOUT': 300,
    }
}
```

---

## Deployment

### Step 1: Run Migrations

```bash
python manage.py migrate credentials
```

This will:
1. Create 5 core tables (UserSession, AuditLog, APIKeyScope, EnhancedAPIKey, APIKeyUsageLog)
2. Create 6 default scopes (full_access, dicom:read, dicom:write, ai:submit, ai:view, users:view)
3. Create EnhancedAPIKey for all existing UserAPIKey instances with `full_access` scope

### Step 2: Enable Feature Flags

Start with tracking only:

```bash
# .env
CREDENTIALS_TRACKING_ENABLED=True
CREDENTIALS_AUDIT_LOGGING_ENABLED=True
CREDENTIALS_RATE_LIMITING_ENABLED=False
```

### Step 3: Monitor Performance

Watch for:
- Database query counts per request
- Redis memory usage
- Audit log table growth rate
- Session table growth rate

Expected overhead:
- Login: ~15-20ms additional latency
- Authenticated requests: ~5-10ms (session activity update)

### Step 4: Enable Rate Limiting (Gradual)

Once tracking is stable:

```bash
CREDENTIALS_RATE_LIMITING_ENABLED=True
```

### Step 5: Configure Cleanup Tasks (Optional)

Create Celery periodic tasks for:

```python
# credentials/tasks.py
@periodic_task(run_every=timedelta(days=1))
def cleanup_old_audit_logs():
    """Delete audit logs older than retention period"""
    cutoff = timezone.now() - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
    deleted = AuditLog.objects.filter(event_timestamp__lt=cutoff).delete()
    logger.info(f"Deleted {deleted[0]} old audit log entries")

@periodic_task(run_every=timedelta(hours=1))
def cleanup_expired_sessions():
    """Terminate expired sessions"""
    expired = UserSession.objects.filter(
        is_active=True,
        expires_at__lt=timezone.now()
    )
    for session in expired:
        session.terminate(reason='expired')
```

---

## Security

### Immutable Audit Logs

AuditLog entries cannot be modified or deleted after creation:

```python
# Attempting to modify raises an exception
log = AuditLog.objects.first()
log.risk_score = 0
log.save()  # Raises: Cannot modify existing AuditLog

# Attempting to delete raises an exception
log.delete()  # Raises: Cannot delete AuditLog entries
```

### Session Hijacking Protection

- **IP Tracking**: Flag sessions when IP address changes
- **Device Fingerprinting**: Detect if browser/OS changes
- **Force Re-authentication**: Terminate suspicious sessions automatically

### API Key Security

- **Scope Enforcement**: Cannot bypass scope restrictions
- **Rate Limiting**: Prevents abuse and DDoS
- **Usage Logging**: Forensic analysis of all requests
- **Automatic Revocation**: After repeated violations

### Brute Force Protection

- **Progressive Delays**: Exponential backoff (2^(attempts-5) seconds, max 60s)
- **IP-Based**: Survives user enumeration attempts
- **Redis-Backed**: Fast, distributed tracking

### Concurrent Session Limits

- **Automatic Enforcement**: No manual intervention needed
- **Oldest First**: Terminates oldest sessions when limit exceeded
- **Configurable**: Per-deployment via settings

---

## Performance Considerations

### Database Impact

**New queries per login:**
- 1 INSERT UserSession
- 1 INSERT AuditLog
- 1 SELECT concurrent session check
- 0-N DELETE old sessions (if limit exceeded)

**Estimated overhead:** ~15-20ms per login

**Indexes:** 10 new indexes across 5 tables (~500MB for 1M users)

### Audit Log Growth

**Assumptions:**
- 1000 active users
- 10 logins per user per day
- 1000 API key requests per day

**Annual growth:**
- Login events: 3.65M records
- API key events: 365K records
- Other events: ~1M records
- **Total:** ~5M audit log entries per year

**Mitigation:**
- Partition by month (Django partitioning)
- Archive to S3
- Cleanup task deletes logs older than retention period

### Redis Usage

**Keys:**
- `login_attempts:{ip}` - ~1KB each, 15-minute TTL
- `rate_limit:{api_key_id}:{period}` - ~1KB each, 1-day TTL

**Estimated memory:** <100MB for 10K concurrent sessions

### Caching Strategy

Cache EnhancedAPIKey lookups (5-minute TTL):

```python
cache_key = f"enhanced_api_key:{api_key.id}"
enhanced_key = cache.get(cache_key)
if not enhanced_key:
    enhanced_key = EnhancedAPIKey.objects.select_related('api_key').prefetch_related('scopes').get(api_key=api_key)
    cache.set(cache_key, enhanced_key, 300)
```

---

## Troubleshooting

### Issue: Sessions not being created

**Solution:** Verify middleware is enabled:

```python
# backend/settings.py
MIDDLEWARE = [
    ...
    'credentials.middleware.RequestContextMiddleware',
    'credentials.middleware.AuditLoggingMiddleware',
]
```

### Issue: Rate limiting not working

**Solution:** Check feature flag:

```python
# backend/settings.py
CREDENTIALS_RATE_LIMITING_ENABLED = True
```

### Issue: Audit logs growing too fast

**Solution:** Enable cleanup task or reduce retention period:

```python
AUDIT_LOG_RETENTION_DAYS = 90  # Reduce from 365
```

### Issue: Redis connection errors

**Solution:** Verify Redis is running and accessible:

```bash
docker-compose ps redis-vetimage
redis-cli -h redis-vetimage ping
```

---

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/yourusername/vetimage/issues
- **Documentation**: `/docs/credentials/`
- **Email**: support@vetimage.com

---

## License

Proprietary - VetImage
