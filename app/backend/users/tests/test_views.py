import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


@pytest.fixture
def api_client():
    """Return API client for testing"""
    return APIClient()


@pytest.fixture
def test_user():
    """Create a test user"""
    return User.objects.create_user(
        email='testuser@example.com',
        password='TestPass123!',
        role=1
    )


@pytest.mark.django_db
class TestRegisterView:
    """Test cases for user registration endpoint"""

    def test_register_success(self, api_client):
        """Test successful user registration"""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!',
            'role': 1
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data
        assert 'user' in response.data
        assert response.data['user']['email'] == 'newuser@example.com'
        assert settings.REFRESH_TOKEN_COOKIE_NAME in response.cookies

        # Verify user was created in database
        user = User.objects.get(email='newuser@example.com')
        assert user.is_active is True

    def test_register_password_mismatch(self, api_client):
        """Test registration with mismatched passwords"""
        url = reverse('register')
        data = {
            'email': 'user@example.com',
            'password': 'Pass123!',
            'password_confirm': 'Different123!',
            'role': 1
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, test_user):
        """Test registration with already existing email"""
        url = reverse('register')
        data = {
            'email': test_user.email,
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!',
            'role': 1
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        """Test registration with weak password"""
        url = reverse('register')
        data = {
            'email': 'user@example.com',
            'password': '123',
            'password_confirm': '123',
            'role': 1
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginView:
    """Test cases for user login endpoint"""

    def test_login_success(self, api_client, test_user):
        """Test successful login"""
        url = reverse('login')
        data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'user' in response.data
        assert response.data['user']['email'] == test_user.email
        # Refresh token is in HttpOnly cookie, not response body
        assert 'refresh' not in response.data
        assert settings.REFRESH_TOKEN_COOKIE_NAME in response.cookies

    def test_login_invalid_credentials(self, api_client, test_user):
        """Test login with invalid credentials"""
        url = reverse('login')
        data = {
            'email': 'testuser@example.com',
            'password': 'WrongPassword'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_is_rate_limited(self, api_client, test_user):
        """After exceeding the login throttle (10/min), further attempts return 429.

        The autouse cache-clear fixture gives this test a fresh throttle window.
        """
        url = reverse('login')
        bad = {'email': 'testuser@example.com', 'password': 'WrongPassword'}
        statuses = [api_client.post(url, bad, format='json').status_code for _ in range(12)]
        assert status.HTTP_429_TOO_MANY_REQUESTS in statuses
        # Earlier attempts are still processed normally (401), not blocked outright.
        assert statuses[0] == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user"""
        url = reverse('login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePass123!'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, api_client):
        """Test login with missing required fields"""
        url = reverse('login')
        data = {
            'email': 'user@example.com'
            # Missing password
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTokenRefreshView:
    """Test cases for token refresh endpoint"""

    def test_refresh_success(self, api_client, test_user):
        """Test successful token refresh with cookie"""
        # First login to get refresh token cookie
        login_url = reverse('login')
        login_data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }
        login_response = api_client.post(login_url, login_data, format='json')
        refresh_cookie = login_response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME]

        # Now test refresh
        refresh_url = reverse('refresh')
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = refresh_cookie.value
        response = api_client.post(refresh_url, {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_refresh_without_cookie(self, api_client):
        """Test token refresh without refresh token cookie"""
        url = reverse('refresh')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ---- Edge-case tests (OMLAB-004) ----

    def _login_and_get_refresh(self, api_client, test_user):
        """Helper: login and return raw refresh cookie value."""
        login_url = reverse('login')
        resp = api_client.post(login_url, {
            'email': 'testuser@example.com',
            'password': 'TestPass123!',
        }, format='json')
        return resp.cookies[settings.REFRESH_TOKEN_COOKIE_NAME].value

    def test_refresh_rotates_cookie(self, api_client, test_user):
        """After refresh, a new (different) refresh token cookie should be set."""
        old_token = self._login_and_get_refresh(api_client, test_user)

        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = old_token
        response = api_client.post(reverse('refresh'), {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        new_token = response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME].value
        assert new_token  # a new cookie was set
        assert new_token != old_token  # rotated to a different value

    def test_old_token_blacklisted_after_rotation(self, api_client, test_user):
        """Re-using the old refresh token after rotation should fail."""
        old_token = self._login_and_get_refresh(api_client, test_user)

        # First refresh — rotates and blacklists old token
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = old_token
        resp1 = api_client.post(reverse('refresh'), {}, format='json')
        assert resp1.status_code == status.HTTP_200_OK

        # Second refresh with the SAME old token — should be blacklisted
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = old_token
        resp2 = api_client.post(reverse('refresh'), {}, format='json')
        assert resp2.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_token_returns_401(self, api_client):
        """An expired refresh token should be rejected."""
        # Craft a token that is definitely expired (just garbage JWT)
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = (
            'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.'
            'eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTAwMDAwMDAwMH0.'
            'fakesignature'
        )
        response = api_client.post(reverse('refresh'), {}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_returns_401(self, api_client):
        """A malformed token string should be rejected."""
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = 'not-a-jwt'
        response = api_client.post(reverse('refresh'), {}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_garbage_token_returns_401(self, api_client):
        """Random bytes as token should be rejected."""
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = 'x' * 200
        response = api_client.post(reverse('refresh'), {}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refreshed_access_preserves_identity(self, api_client, test_user):
        """The new access token should belong to the same user."""
        from rest_framework_simplejwt.tokens import AccessToken

        refresh_value = self._login_and_get_refresh(api_client, test_user)
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = refresh_value
        response = api_client.post(reverse('refresh'), {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        token = AccessToken(response.data['access'])
        assert token['user_id'] == test_user.pk

    def test_refresh_cookie_has_httponly(self, api_client, test_user):
        """Refresh cookie must have httponly flag."""
        refresh_value = self._login_and_get_refresh(api_client, test_user)
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = refresh_value
        response = api_client.post(reverse('refresh'), {}, format='json')

        cookie = response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME]
        assert cookie['httponly'] is True

    def test_refresh_cookie_has_samesite(self, api_client, test_user):
        """Refresh cookie must have samesite flag."""
        refresh_value = self._login_and_get_refresh(api_client, test_user)
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = refresh_value
        response = api_client.post(reverse('refresh'), {}, format='json')

        cookie = response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME]
        assert cookie['samesite'] in ('Lax', 'Strict', 'None')


@pytest.mark.django_db
class TestLogoutView:
    """Test cases for logout endpoint"""

    def test_logout_success(self, api_client, test_user):
        """Test successful logout"""
        # First login to get access token and refresh cookie
        login_url = reverse('login')
        login_data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }
        login_response = api_client.post(login_url, login_data, format='json')
        access_token = login_response.data['access']
        refresh_cookie = login_response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME]

        # Logout (requires JWT auth + refresh token in cookie)
        logout_url = reverse('logout')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        api_client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = refresh_cookie.value
        response = api_client.post(logout_url, {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Logged out successfully'

        # Verify refresh token cookie is deleted
        assert settings.REFRESH_TOKEN_COOKIE_NAME in response.cookies
        assert response.cookies[settings.REFRESH_TOKEN_COOKIE_NAME].value == ''

    def test_logout_unauthenticated(self, api_client):
        """Test logout without authentication returns 401"""
        url = reverse('logout')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfileView:
    """Test cases for user profile endpoint"""

    def test_get_profile_authenticated(self, api_client, test_user):
        """Test getting profile while authenticated"""
        # Login first to get access token
        login_url = reverse('login')
        login_data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }
        login_response = api_client.post(login_url, login_data, format='json')
        access_token = login_response.data['access']

        # Get profile
        profile_url = reverse('profile')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get(profile_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == test_user.email
        assert response.data['role'] == test_user.role

    def test_get_profile_unauthenticated(self, api_client):
        """Test getting profile without authentication"""
        url = reverse('profile')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestChangePasswordView:
    """Test cases for change password endpoint"""

    def test_change_password_success(self, api_client, test_user):
        """Test successful password change"""
        # Login first
        login_url = reverse('login')
        login_data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }
        login_response = api_client.post(login_url, login_data, format='json')
        access_token = login_response.data['access']

        # Change password (POST, not PUT)
        change_url = reverse('change-password')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        change_data = {
            'old_password': 'TestPass123!',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'NewPass456!'
        }
        response = api_client.post(change_url, change_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Password changed successfully'

        # Verify new password works
        test_user.refresh_from_db()
        assert test_user.check_password('NewPass456!')

    def test_change_password_wrong_old_password(self, api_client, test_user):
        """Test password change with wrong old password"""
        # Login first
        login_url = reverse('login')
        login_data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }
        login_response = api_client.post(login_url, login_data, format='json')
        access_token = login_response.data['access']

        # Try to change password with wrong old password
        change_url = reverse('change-password')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        change_data = {
            'old_password': 'WrongPassword',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'NewPass456!'
        }
        response = api_client.post(change_url, change_data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_unauthenticated(self, api_client):
        """Test password change without authentication"""
        url = reverse('change-password')
        change_data = {
            'old_password': 'TestPass123!',
            'new_password': 'NewPass456!',
            'new_password_confirm': 'NewPass456!'
        }
        response = api_client.post(url, change_data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPasswordResetRequestView:
    """Test cases for password reset request (forgot password) endpoint"""

    def test_password_reset_request_existing_email(self, api_client, test_user):
        """Test password reset request with existing email returns 200"""
        url = reverse('forgot-password')
        data = {'email': test_user.email}
        with patch('django.core.mail.send_mail') as mock_send:
            response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        mock_send.assert_called_once()

    def test_password_reset_request_nonexistent_email(self, api_client):
        """Test password reset request with unknown email still returns 200 (no enumeration)"""
        url = reverse('forgot-password')
        data = {'email': 'nonexistent@example.com'}
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data

    def test_password_reset_request_invalid_email(self, api_client):
        """Test password reset request with invalid email returns 400"""
        url = reverse('forgot-password')
        data = {'email': 'not-an-email'}
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_request_missing_email(self, api_client):
        """Test password reset request without email field returns 400"""
        url = reverse('forgot-password')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_request_creates_audit_log(self, api_client, test_user):
        """Test that password reset request creates an audit log entry"""
        from credentials.models import AuditLog

        url = reverse('forgot-password')
        data = {'email': test_user.email}
        with patch('django.core.mail.send_mail'):
            api_client.post(url, data, format='json')

        assert AuditLog.objects.filter(
            user=test_user,
            event_type='password_reset_request',
        ).exists()


@pytest.mark.django_db
class TestPasswordResetConfirmView:
    """Test cases for password reset confirmation endpoint"""

    def _make_token_and_uid(self, user):
        """Helper to generate a valid token and encoded UID for a user."""
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        return uid, token

    def test_password_reset_confirm_success(self, api_client, test_user):
        """Test successful password reset with valid token"""
        uid, token = self._make_token_and_uid(test_user)
        url = reverse('reset-password')
        data = {
            'uid': uid,
            'token': token,
            'new_password': 'NewSecure456!',
            'new_password_confirm': 'NewSecure456!',
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Password has been reset successfully.'

        # Verify new password works
        test_user.refresh_from_db()
        assert test_user.check_password('NewSecure456!')

    def test_password_reset_confirm_invalid_token(self, api_client, test_user):
        """Test password reset with invalid token returns 400"""
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))
        url = reverse('reset-password')
        data = {
            'uid': uid,
            'token': 'invalid-token',
            'new_password': 'NewSecure456!',
            'new_password_confirm': 'NewSecure456!',
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_confirm_invalid_uid(self, api_client):
        """Test password reset with invalid UID returns 400"""
        url = reverse('reset-password')
        data = {
            'uid': 'invaliduid',
            'token': 'some-token',
            'new_password': 'NewSecure456!',
            'new_password_confirm': 'NewSecure456!',
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_confirm_password_mismatch(self, api_client, test_user):
        """Test password reset with mismatched passwords returns 400"""
        uid, token = self._make_token_and_uid(test_user)
        url = reverse('reset-password')
        data = {
            'uid': uid,
            'token': token,
            'new_password': 'NewSecure456!',
            'new_password_confirm': 'Different789!',
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_confirm_weak_password(self, api_client, test_user):
        """Test password reset with weak password returns 400"""
        uid, token = self._make_token_and_uid(test_user)
        url = reverse('reset-password')
        data = {
            'uid': uid,
            'token': token,
            'new_password': '123',
            'new_password_confirm': '123',
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_token_used_twice_fails(self, api_client, test_user):
        """Test that a token cannot be reused after password reset"""
        uid, token = self._make_token_and_uid(test_user)
        url = reverse('reset-password')
        data = {
            'uid': uid,
            'token': token,
            'new_password': 'NewSecure456!',
            'new_password_confirm': 'NewSecure456!',
        }
        # First use — should succeed
        response1 = api_client.post(url, data, format='json')
        assert response1.status_code == status.HTTP_200_OK

        # Second use — token is invalidated because password changed
        response2 = api_client.post(url, data, format='json')
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_creates_audit_log(self, api_client, test_user):
        """Test that password reset creates an audit log entry"""
        from credentials.models import AuditLog

        uid, token = self._make_token_and_uid(test_user)
        url = reverse('reset-password')
        data = {
            'uid': uid,
            'token': token,
            'new_password': 'NewSecure456!',
            'new_password_confirm': 'NewSecure456!',
        }
        api_client.post(url, data, format='json')

        assert AuditLog.objects.filter(
            user=test_user,
            event_type='password_reset_complete',
        ).exists()
