"""
Platform-admin routes (`/api/admin/`).

Every view here is gated on `core.permissions.IsPlatformStaff`. Kept in its own
module so the cross-clinic surface is easy to audit in one place.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_admin import (
    AdminClinicViewSet,
    AdminPlatformSummaryView,
    AdminStatisticsView,
)

router = DefaultRouter()
router.register(r'clinics', AdminClinicViewSet, basename='admin-clinic')

urlpatterns = [
    path('summary/', AdminPlatformSummaryView.as_view(), name='admin-summary'),
    path('statistics/', AdminStatisticsView.as_view(), name='admin-statistics'),
    path('', include(router.urls)),
]
