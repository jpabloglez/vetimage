from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth import login as django_login
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Create your views here.

from users.models import (
    User,
    UserProfile
)
from users.serializers import (
    UserSerializer,
    #UserManagerSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserAuthSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

from rest_framework import status, generics
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings

from users.permissions import IsAdminUserOrReadOnly

#class UserViewSet(viewsets.ModelViewSet):

   
@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class UserListView(APIView):
    __doc__ = """ User List View """

    def get(self, request, format=None):
        users = User.objects.filter(is_active=True)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class UserDetailView(APIView):
    __doc__ = """ User Detail View """

    def get(self, request, pk, format=None):
        user = User.objects.get(pk=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


    def put(self, request, pk, format=None):
        user = User.objects.get(pk=pk)
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        user = User.objects.get(pk=pk)
        # user.delete()
        user.deleted_at = timezone.now()
        user.is_active = False
        return Response(status=status.HTTP_204_NO_CONTENT)

class UserProfileDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        serializer = UserProfileSerializer(user.userprofile)
        return Response(serializer.data, status.HTTP_200_OK)

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def complete_profile(self, request):
        """
        Complete user profile with department/team info for Monitor page.

        POST /api/users/profile/complete/
        Body: {
            "department": "Radiology",
            "job_title": "Radiologist",
            "team_name": "MRI Team",
            "is_sharing_jobs_with_colleagues": true
        }
        """
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'User profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update profile fields
        profile.department = request.data.get('department', '')
        profile.job_title = request.data.get('job_title', '')
        profile.team_name = request.data.get('team_name', '')
        profile.is_sharing_jobs_with_colleagues = request.data.get('is_sharing_jobs_with_colleagues', False)
        if 'language' in request.data:
            lang = request.data['language']
            if lang in ('en', 'es', 'pt'):
                profile.language = lang
        profile.save()

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def colleagues(self, request):
        """
        Get colleagues in same organization who share their work.

        GET /api/users/profile/colleagues/

        Returns colleagues with is_sharing_jobs_with_colleagues=True
        Only returns: name, department, team, job_title (no PHI).
        """
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        if not profile.organization:
            return Response([], status=status.HTTP_200_OK)

        # Get colleagues in same organization who are sharing
        colleagues = UserProfile.objects.filter(
            organization=profile.organization,
            is_sharing_jobs_with_colleagues=True
        ).exclude(user=request.user).select_related('user')

        # Return minimal colleague info
        colleague_data = [{
            'id': c.id,
            'first_name': c.first_name,
            'last_name': c.last_name,
            'department': c.department,
            'job_title': c.job_title,
            'team_name': c.team_name,
        } for c in colleagues]

        return Response(colleague_data, status=status.HTTP_200_OK)

@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class UserProfileListView(APIView):
    __doc__ = """ User Profile List View """
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        #user = request.user
        #serializer = UserProfileSerializer(user.userprofile)
        users = UserProfile.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        serializer = UserProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class UserProfileDetailView(APIView):
    __doc__ = """ User Profile Detail View """

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        # try:
        #     return UserProfile.objects.get(pk=pk)
        # except UserProfile.DoesNotExist:
        #     raise(status.HTTP_404_NOT_FOUND)
        return UserProfile.objects.get(pk=pk)


    def get(self, request, pk, format=None):
        user = self.get_object(pk)
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

        #user = UserProfile.objects.get(pk=pk)
        #serializer = UserProfileSerializer(user)
        #return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, format=None):
        user = self.get_object(pk)
        serializer = UserProfileSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        """ Soft deletion of the user profile """
        user = self.get_object(pk)
        user.deleted_at = timezone.now()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
        # Complete deletion of the user profile
        #user = self.get_object(pk)
        #user.delete()
        #return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class AvatarUploadView(APIView):
    """
    Upload user avatar image.
    PATCH /users/auth/profile/upload_avatar/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def patch(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response({'detail': 'No image provided.'}, status=400)
        if image.size > 5 * 1024 * 1024:
            return Response({'detail': 'Image exceeds 5 MB limit.'}, status=400)
        profile = request.user.userprofile
        profile.image = image
        profile.save()
        return Response({'image_url': request.build_absolute_uri(profile.image.url)})


# ============================================================================
# JWT Authentication Views
# ============================================================================


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint
    POST /api/auth/register/
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    throttle_scope = 'register'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens for newly registered user
        refresh = RefreshToken.for_user(user)

        response = Response({
            'user': UserAuthSerializer(user).data,
            'message': 'User registered successfully',
        }, status=status.HTTP_201_CREATED)

        # Set refresh token in HttpOnly cookie
        cookie_kwargs = {
            'key': settings.REFRESH_TOKEN_COOKIE_NAME,
            'value': str(refresh),
            'max_age': settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
            'secure': settings.REFRESH_TOKEN_COOKIE_SECURE,
            'httponly': settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
            'samesite': settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        }
        if settings.REFRESH_TOKEN_COOKIE_DOMAIN:
            cookie_kwargs['domain'] = settings.REFRESH_TOKEN_COOKIE_DOMAIN
        response.set_cookie(**cookie_kwargs)

        # Return access token in response body
        response.data['access'] = str(refresh.access_token)

        return response


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom login endpoint with cookie-based refresh token
    POST /api/auth/login/
    Body: { "email": "user@example.com", "password": "password123" }

    CSRF exemption: Uses only JWT authentication, not session auth with CSRF.
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication required for login
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        # Get the authenticated user from serializer
        user = serializer.user

        # Create Django session for WebSocket authentication
        # This enables WebSocket connections to authenticate via session cookies
        django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Create response with user data and access token
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)

        # Set refresh token in HttpOnly cookie
        cookie_kwargs = {
            'key': settings.REFRESH_TOKEN_COOKIE_NAME,
            'value': serializer.validated_data['refresh'],
            'max_age': settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
            'secure': settings.REFRESH_TOKEN_COOKIE_SECURE,
            'httponly': settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
            'samesite': settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        }
        if settings.REFRESH_TOKEN_COOKIE_DOMAIN:
            cookie_kwargs['domain'] = settings.REFRESH_TOKEN_COOKIE_DOMAIN
        response.set_cookie(**cookie_kwargs)

        # Don't send refresh token in response body (already in cookie)
        response.data.pop('refresh', None)

        return response


@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class CustomTokenRefreshView(APIView):
    """
    Custom token refresh endpoint that reads refresh token from cookie
    POST /api/auth/refresh/

    CSRF exemption: Uses HttpOnly cookies, not session auth with CSRF.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No authentication required for refresh
    throttle_scope = 'token_refresh'

    def post(self, request):
        # Get refresh token from cookie
        refresh_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)

        if not refresh_token:
            return Response(
                {'detail': 'Refresh token not found in cookies'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            response = Response({
                'access': access_token,
            }, status=status.HTTP_200_OK)

            # If token rotation is enabled, generate a new refresh token
            if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
                # Blacklist the old token before issuing a new one
                if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION', False):
                    try:
                        refresh.blacklist()
                    except AttributeError:
                        pass  # Blacklist app not installed

                # Generate a new refresh token with fresh jti/exp/iat
                new_refresh = RefreshToken.for_user(
                    User.objects.get(pk=refresh['user_id'])
                )

                cookie_kwargs = {
                    'key': settings.REFRESH_TOKEN_COOKIE_NAME,
                    'value': str(new_refresh),
                    'max_age': settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
                    'secure': settings.REFRESH_TOKEN_COOKIE_SECURE,
                    'httponly': settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
                    'samesite': settings.REFRESH_TOKEN_COOKIE_SAMESITE,
                }
                if settings.REFRESH_TOKEN_COOKIE_DOMAIN:
                    cookie_kwargs['domain'] = settings.REFRESH_TOKEN_COOKIE_DOMAIN
                response.set_cookie(**cookie_kwargs)

            return response

        except TokenError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )


@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class LogoutView(APIView):
    """
    Logout endpoint - blacklists refresh token
    POST /api/auth/logout/

    CSRF exemption: Uses JWT authentication, not session-based CSRF.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            # Get refresh token from cookie
            refresh_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)

            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            response = Response({
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)

            # Delete refresh token cookie
            response.delete_cookie(
                key=settings.REFRESH_TOKEN_COOKIE_NAME,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
            )

            return response

        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileAuthView(generics.RetrieveUpdateAPIView):
    """
    Get or update authenticated user profile
    GET/PATCH /api/auth/profile/
    """
    serializer_class = UserAuthSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([AllowAny])  # API key provides authentication
def api_key_auth(request):
    """
    Authenticate using API key and return JWT tokens.

    Request body:
    {
        "api_key": "oml_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }

    Returns:
    {
        "access": "<jwt_access_token>",
        "refresh": "<jwt_refresh_token>",
        "user": {
            "id": 10,
            "email": "user@example.com",
            "role": 1
        }
    }
    """
    from .models import UserAPIKey

    api_key = request.data.get('api_key')

    if not api_key:
        return Response(
            {'error': 'api_key field is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Hash the provided key
    key_hash = UserAPIKey.hash_key(api_key)

    try:
        # Lookup API key by hash
        api_key_obj = UserAPIKey.objects.select_related('user').get(
            key_hash=key_hash
        )

        # Validate key (active + not expired)
        if not api_key_obj.is_valid():
            if not api_key_obj.is_active:
                error_msg = 'API key has been revoked'
            else:
                error_msg = 'API key has expired'

            return Response(
                {'error': error_msg},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Record usage
        api_key_obj.record_usage()

        user = api_key_obj.user

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
            }
        }, status=status.HTTP_200_OK)

    except UserAPIKey.DoesNotExist:
        return Response(
            {'error': 'Invalid API key'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'error': 'Authentication failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class ChangePasswordView(APIView):
    """
    Change password endpoint
    POST /api/auth/change-password/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            user = request.user

            # Check old password
            if not user.check_password(serializer.data.get('old_password')):
                return Response(
                    {'old_password': ['Wrong password.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(serializer.data.get('new_password'))
            user.save()

            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class PasswordResetRequestView(APIView):
    """
    Request a password reset email
    POST /api/auth/forgot-password/
    Body: { "email": "user@example.com" }

    Always returns 200 to prevent user enumeration.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset'

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        from django.core.mail import send_mail

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Return 200 anyway to prevent user enumeration
            return Response(
                {'message': 'If an account with this email exists, a password reset link has been sent.'},
                status=status.HTTP_200_OK,
            )

        # Generate token and encoded UID
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Build reset link
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        reset_link = f"{frontend_url}/reset-password?uid={uid}&token={token}"

        # Send email
        send_mail(
            subject='Password Reset Request — VetImage',
            message=f'Click the link below to reset your password:\n\n{reset_link}\n\nIf you did not request this, please ignore this email.',
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=[email],
            fail_silently=True,
        )

        # Create audit log entry if credentials app is available
        try:
            from credentials.models import AuditLog
            AuditLog.objects.create(
                user=user,
                event_type='password_reset_request',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                metadata={'email': email},
            )
        except Exception:
            pass  # Don't fail if audit logging is unavailable

        return Response(
            {'message': 'If an account with this email exists, a password reset link has been sent.'},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=['Auth'], responses=OpenApiTypes.OBJECT)
class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token
    POST /api/auth/reset-password/
    Body: { "uid": "...", "token": "...", "new_password": "...", "new_password_confirm": "..." }
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset'

    def post(self, request):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Decode UID
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'detail': 'Invalid reset link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate token
        if not default_token_generator.check_token(user, serializer.validated_data['token']):
            return Response(
                {'detail': 'Invalid or expired reset token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Create audit log entry
        try:
            from credentials.models import AuditLog
            AuditLog.objects.create(
                user=user,
                event_type='password_reset_complete',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            )
        except Exception:
            pass

        return Response(
            {'message': 'Password has been reset successfully.'},
            status=status.HTTP_200_OK,
        )