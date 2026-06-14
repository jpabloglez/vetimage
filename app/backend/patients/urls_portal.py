from django.urls import path
from .views_portal import OwnerPortalDashboardView, OwnerAccountProvisionView

urlpatterns = [
    path('dashboard/', OwnerPortalDashboardView.as_view(), name='owner-portal-dashboard'),
    path('owners/<int:owner_id>/account/', OwnerAccountProvisionView.as_view(),
         name='owner-portal-provision'),
]
