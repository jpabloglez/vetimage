from django.urls import path
from rest_framework.routers import DefaultRouter
from users.views_invitations import AcceptInvitationView, ClinicInvitationViewSet
from users.views import (
    UserListView,
    UserDetailView,
    UserProfileViewSet,
    UserProfileListView,
    UserProfileDetailView,
    AvatarUploadView,
    # JWT Authentication Views
    RegisterView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    WebSocketTicketView,
    LogoutView,
    UserProfileAuthView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    api_key_auth,
)

# Using router for UserProfileViewSet (provides complete_profile, colleagues actions)
router = DefaultRouter()
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'clinic/invitations', ClinicInvitationViewSet, basename='clinic-invitation')

# User Management URLs
user_patterns = [
    path(
        '',
        UserListView.as_view(),
        name='users-list'),
    path(
        '<int:pk>/',
        UserDetailView.as_view(),
        name='users-detail'),
    path(
        'profile-list/',
        UserProfileListView.as_view(),
        name='users-profile-list'),
    path(
        'profile-detail/<int:pk>/',
        UserProfileDetailView.as_view(),
        name='users-profile-detail')
]

# JWT Authentication URLs
auth_patterns = [
    # Authentication
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/api-key/', api_key_auth, name='api-key-auth'),
    path('auth/ws-ticket/', WebSocketTicketView.as_view(), name='ws-ticket'),
    path('clinic/invitations/accept/<uuid:token>/',
         AcceptInvitationView.as_view(), name='accept-invitation'),

    # User Profile
    path('auth/profile/', UserProfileAuthView.as_view(), name='profile'),
    path('auth/profile/upload_avatar/', AvatarUploadView.as_view(), name='upload-avatar'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/forgot-password/', PasswordResetRequestView.as_view(), name='forgot-password'),
    path('auth/reset-password/', PasswordResetConfirmView.as_view(), name='reset-password'),
]

# Combine all patterns
urlpatterns = router.urls + user_patterns + auth_patterns

