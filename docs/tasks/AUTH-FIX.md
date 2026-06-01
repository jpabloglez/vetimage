# Authentication Fix - Token Persistence on Page Refresh

## Problem

Users were experiencing authentication issues where:
1. After successful login, they would get a `401 Unauthorized` error
2. On page refresh, they were logged out and redirected to the login page

**Error Message:**
```
GET http://localhost:3080/users/auth/profile/ 401 (Unauthorized)
```

## Root Cause

The authentication system uses two types of tokens:
1. **Access Token** (short-lived, ~15 minutes)
   - Stored in memory (`apiClient.accessToken`)
   - Used for API requests via `Authorization: Bearer <token>` header

2. **Refresh Token** (long-lived, ~7 days)
   - Stored in HttpOnly secure cookie
   - Used to obtain new access tokens

**The Issue:**
- On login, the access token was stored in memory only
- On page refresh, memory is cleared, losing the access token
- The `AuthContext` initialization tried to call `getProfile()` without an access token
- The request failed with 401 **before** attempting to refresh the token

## Solution

Modified the `AuthContext` initialization to:
1. **First** refresh the access token using the refresh token cookie
2. **Then** fetch the user profile with the refreshed access token

### Changes Made

**1. Updated `app/frontend/src/contexts/AuthContext.tsx`:**

```typescript
// BEFORE (broken)
const initAuth = async () => {
  try {
    // Tries to get profile without access token - FAILS with 401
    const profile = await apiClient.getProfile();
    setUser(profile);
  } catch (error) {
    console.log('No active session found');
    setUser(null);
  } finally {
    setIsLoading(false);
  }
};

// AFTER (fixed)
const initAuth = async () => {
  try {
    // First, refresh the access token from the refresh token cookie
    await apiClient.refreshToken();

    // Now get user profile with the refreshed access token
    const profile = await apiClient.getProfile();
    setUser(profile);
  } catch (error) {
    console.log('No active session found');
    setUser(null);
  } finally {
    setIsLoading(false);
  }
};
```

**2. Added public `refreshToken()` method to `app/frontend/src/utils/api.ts`:**

```typescript
/**
 * Public method to refresh access token
 * Used on app initialization to restore session from refresh token cookie
 */
async refreshToken(): Promise<void> {
  await this.refreshAccessToken();
}
```

## How It Works Now

### Login Flow
```
1. User submits credentials
   ↓
2. POST /users/auth/login/
   ↓
3. Backend returns:
   - access token (in response body)
   - refresh token (in HttpOnly cookie)
   ↓
4. Frontend stores:
   - access token → memory (apiClient.accessToken)
   - refresh token → cookie (automatic)
   ↓
5. User is authenticated
```

### Page Refresh Flow
```
1. Page loads, memory is cleared
   ↓
2. AuthContext.initAuth() runs
   ↓
3. POST /users/auth/refresh/
   - Sends refresh token cookie
   ↓
4. Backend returns new access token
   ↓
5. Access token stored in memory
   ↓
6. GET /users/auth/profile/
   - Uses refreshed access token
   ↓
7. User stays authenticated ✓
```

### API Request Flow (with expired access token)
```
1. API request with access token
   ↓
2. Backend returns 401 (token expired)
   ↓
3. Frontend automatically calls refreshAccessToken()
   ↓
4. POST /users/auth/refresh/
   ↓
5. New access token obtained
   ↓
6. Retry original request with new token
   ↓
7. Request succeeds ✓
```

## Testing

### Before Fix
1. Login → Success
2. Navigate to any page → GET profile → **401 Error**
3. Page refresh → **Logged out and redirected to login**

### After Fix
1. Login → Success
2. Navigate to any page → Auto-refresh token → GET profile → **Success** ✓
3. Page refresh → Auto-refresh token → **Stays logged in** ✓

### Manual Testing Steps

1. **Login Test:**
   ```bash
   # Open browser console
   # Login to the application
   # Check Network tab - should see:
   POST /users/auth/login/ → 200 OK
   POST /users/auth/refresh/ → 200 OK  # Auto-called on init
   GET /users/auth/profile/ → 200 OK
   ```

2. **Refresh Test:**
   ```bash
   # While logged in, refresh the page (F5)
   # Check Network tab - should see:
   POST /users/auth/refresh/ → 200 OK  # Gets new access token
   GET /users/auth/profile/ → 200 OK   # Uses refreshed token
   # User should remain logged in ✓
   ```

3. **Expired Token Test:**
   ```bash
   # Login and wait 15+ minutes (access token expires)
   # Make any API request
   # Check Network tab - should see:
   GET /api/some-endpoint/ → 401
   POST /users/auth/refresh/ → 200 OK  # Auto-refresh
   GET /api/some-endpoint/ → 200 OK    # Retry succeeds
   ```

## Security Notes

**Why access tokens are in memory (not localStorage):**
- Prevents XSS attacks from stealing tokens
- Token automatically cleared on tab close
- Cannot be accessed by malicious scripts

**Why refresh tokens are in HttpOnly cookies:**
- Cannot be accessed by JavaScript (XSS protection)
- Automatically sent with requests
- Secure flag ensures HTTPS-only transmission
- SameSite flag prevents CSRF attacks

**Token Lifetimes:**
- Access Token: 15 minutes (configurable in Django settings)
- Refresh Token: 7 days (configurable in Django settings)

## Backend Configuration

Ensure these settings are configured in `backend/settings.py`:

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# CORS settings for cookies
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Session cookie settings
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'
```

## Troubleshooting

### Issue: Still getting 401 after fix

**Check 1: Refresh token cookie exists**
```bash
# In browser DevTools → Application → Cookies
# Should see: refresh_token cookie for localhost:3080
```

**Check 2: CORS credentials enabled**
```bash
# In Network tab, check request headers:
credentials: 'include'  # Should be present
```

**Check 3: Backend allows credentials**
```bash
# In response headers:
Access-Control-Allow-Credentials: true
```

### Issue: Refresh token endpoint returns 401

**Possible causes:**
1. Refresh token cookie expired (> 7 days old)
2. Refresh token blacklisted (after logout)
3. CORS not allowing credentials

**Solution:**
- Clear cookies and login again
- Check backend logs for specific error
- Verify CORS settings

### Issue: CORS errors

**Error:** `Access to fetch at '...' from origin '...' has been blocked by CORS policy`

**Solution:**
```python
# In backend/settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Add your frontend URL
]
CORS_ALLOW_CREDENTIALS = True
```

## Related Files

- `/home/jpablo/code/web-apps/openmedlab/app/frontend/src/contexts/AuthContext.tsx`
- `/home/jpablo/code/web-apps/openmedlab/app/frontend/src/utils/api.ts`
- `/home/jpablo/code/web-apps/openmedlab/app/backend/users/views.py`
- `/home/jpablo/code/web-apps/openmedlab/app/backend/users/urls.py`
- `/home/jpablo/code/web-apps/openmedlab/app/backend/backend/settings.py`

## Additional Resources

- [Django REST Framework SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [MDN: HTTP Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
