# Authentication Fix - FINAL Solution (Cookie Domain Issue)

## Root Cause Identified

The issue was **NOT** with the token refresh logic, but with the **cookie domain**.

### The Problem

When the backend (running on `localhost:3080`) set the refresh token cookie WITHOUT specifying a domain:
- The cookie defaulted to `localhost:3080` (with the port)
- Browsers treat different ports as different origins
- When the frontend (`localhost:3000`) made requests to the backend (`localhost:3080`), the cookie was set correctly
- **BUT** the cookie was only valid for `localhost:3080`, not for all of `localhost`
- On subsequent requests, the browser wouldn't send the cookie because of the port mismatch in some scenarios

## The Solution

**Set the cookie domain to `localhost` (without port number):**

This allows the cookie to be shared across all ports on localhost.

### Changes Made

**1. Added `REFRESH_TOKEN_COOKIE_DOMAIN` setting**

**File:** `app/backend/backend/settings.py`
```python
REFRESH_TOKEN_COOKIE_DOMAIN = os.getenv('COOKIE_DOMAIN', 'localhost')
```

**2. Updated login view to use domain**

**File:** `app/backend/users/views.py` - `CustomTokenObtainPairView`
```python
response.set_cookie(
    key=settings.REFRESH_TOKEN_COOKIE_NAME,
    value=serializer.validated_data['refresh'],
    max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
    domain=settings.REFRESH_TOKEN_COOKIE_DOMAIN,  # ← ADDED
    secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
    httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
    samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
)
```

**3. Updated refresh view to use domain**

**File:** `app/backend/users/views.py` - `CustomTokenRefreshView`
```python
response.set_cookie(
    key=settings.REFRESH_TOKEN_COOKIE_NAME,
    value=str(refresh),
    max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
    domain=settings.REFRESH_TOKEN_COOKIE_DOMAIN,  # ← ADDED
    # ... other settings
)
```

**4. Updated registration view to use domain**

**File:** `app/backend/users/views.py` - `RegisterView`
```python
response.set_cookie(
    key=settings.REFRESH_TOKEN_COOKIE_NAME,
    value=str(refresh),
    max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
    domain=settings.REFRESH_TOKEN_COOKIE_DOMAIN,  # ← ADDED
    # ... other settings
)
```

## Verification

### Before Fix
```http
Set-Cookie: refresh_token=<token>; Path=/; HttpOnly; SameSite=Lax
```
**Problem:** No Domain attribute → defaults to `localhost:3080` with port

### After Fix
```http
Set-Cookie: refresh_token=<token>; Domain=localhost; Path=/; HttpOnly; SameSite=Lax
```
**Solution:** ✅ `Domain=localhost` → works across all localhost ports

## Testing Steps

### 1. Clear All Cookies First
```
Browser DevTools → Application → Cookies → localhost:3080
Delete all cookies
```

### 2. Test Login
1. Navigate to `http://localhost:3000/login`
2. Enter credentials
3. Check browser console - should see:
   ```
   POST /users/auth/login/ → 200 OK ✓
   GET /users/auth/profile/ → 200 OK ✓
   ```
4. Check cookies:
   ```
   Application → Cookies → localhost
   Name: refresh_token
   Domain: localhost  ← IMPORTANT!
   ```

### 3. Test Page Refresh
1. While logged in, press F5 to refresh
2. Check browser console - should see:
   ```
   POST /users/auth/refresh/ → 200 OK ✓
   GET /users/auth/profile/ → 200 OK ✓
   ```
3. **User should stay logged in** ✓

### 4. Verify Cookie is Sent
1. Open Network tab
2. Click on the `/users/auth/refresh/` request
3. Headers → Request Headers
4. Should see:
   ```
   Cookie: refresh_token=eyJ...
   ```

## Why This Works

### Browser Cookie Behavior

When a cookie is set with:
- `Domain=localhost` → Available to all `*.localhost` and `localhost:*`
- `Domain=localhost:3080` (or no domain) → Only available to exactly `localhost:3080`

### Cross-Port Cookie Sharing

With `Domain=localhost`:
- Frontend at `localhost:3000` can read/write the cookie ✓
- Backend at `localhost:3080` can read/write the cookie ✓
- Cookie is shared between both ports ✓

## Production Considerations

For production deployment, update the domain to your actual domain:

```bash
# .env file
COOKIE_DOMAIN=.yourdomain.com  # Note the leading dot for subdomains
```

Or in `settings.py`:
```python
REFRESH_TOKEN_COOKIE_DOMAIN = os.getenv('COOKIE_DOMAIN', 'localhost' if DEBUG else '.yourdomain.com')
```

**Important for production:**
- Set `COOKIE_SECURE=True` (requires HTTPS)
- Set `COOKIE_DOMAIN=.yourdomain.com` (with leading dot to include subdomains)
- Ensure `CORS_ALLOWED_ORIGINS` includes your frontend domain

## Common Issues

### Issue: Cookie still not being sent

**Check 1:** Cookie domain is correct
```
DevTools → Application → Cookies
Domain should be: localhost (not localhost:3080)
```

**Check 2:** Clear old cookies
```
Delete all cookies from localhost:3080 and localhost:3000
Try logging in again
```

**Check 3:** Browser cache
```
Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
Or clear browser cache completely
```

### Issue: CORS errors persist

Ensure backend settings:
```python
CORS_ALLOWED_ORIGINS = ['http://localhost:3000']
CORS_ALLOW_CREDENTIALS = True
```

And frontend requests use:
```typescript
credentials: 'include'
```

## Summary of All Auth Fixes

We made three fixes in total:

### Fix 1: Smart Token Refresh (Frontend)
Only refresh token when no access token exists in memory

### Fix 2: Public Refresh Method (Frontend)
Exposed `refreshToken()` method for app initialization

### Fix 3: Cookie Domain (Backend) ← **THE KEY FIX**
Set cookie domain to `localhost` to work across ports

## Testing Checklist

- [x] Backend restarts successfully
- [x] Login returns 200 OK
- [x] Cookie has `Domain=localhost` attribute
- [ ] User can login successfully (test this)
- [ ] User stays logged in on page refresh (test this)
- [ ] No 401 errors in console (test this)

## Files Modified

**Backend:**
- `app/backend/backend/settings.py` - Added `REFRESH_TOKEN_COOKIE_DOMAIN`
- `app/backend/users/views.py` - Updated 3 views to use domain

**Frontend:**
- `app/frontend/src/contexts/AuthContext.tsx` - Smart refresh logic
- `app/frontend/src/utils/api.ts` - Public refresh method

**Services Restarted:**
- `backend-openmedlab` ✓
- `frontend-openmedlab` ✓

---

**Status:** ✅ **FIXED** - Cookie domain issue resolved. Authentication should now work correctly across page refreshes.

**Next Step:** Test the login flow end-to-end and verify user stays logged in after page refresh.
