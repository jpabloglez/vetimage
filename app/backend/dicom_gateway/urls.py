"""
URL Configuration for DICOM Gateway API.

Provides REST API endpoints for DICOM transfer monitoring.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import DICOMTransferViewSet, DICOMTransactionViewSet, pacs_lookup

# Create router and register viewsets
router = DefaultRouter()
router.register(r'transfers', DICOMTransferViewSet, basename='dicom-transfer')
router.register(r'transactions', DICOMTransactionViewSet, basename='dicom-transaction')

urlpatterns = [
    path('', include(router.urls)),
    path('pacs/lookup/', pacs_lookup, name='pacs-lookup'),
]
