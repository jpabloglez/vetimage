"""
DICOM Images URL Configuration

URL routing for DICOM upload and DICOMweb endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DicomUploadView,
    MedicalImageUploadView,
    StudyListView,
    SeriesListView,
    InstanceListView,
    StorageQuotaView,
    DeleteStudyView,
    WADORSFrameRetrieveView,
    WADORSInstanceRetrieveView,
    WADORSMetadataRetrieveView,
    # New endpoints
    SeriesThumbnailView,
    GenerateThumbnailsView,
    AdvancedSearchView,
    SavedSearchListCreateView,
    SavedSearchDetailView,
    AnnotationListCreateView,
    AnnotationDetailView,
)
from .views_anonymization import AnonymizationJobViewSet
from .views_tag_editor import DicomTagListView, DicomTagUpdateView
from .views_conversion import ConversionJobViewSet
from .views_batch import BatchOperationViewSet

app_name = 'dicom_images'

# Router for viewsets
router = DefaultRouter()
router.register('anonymize', AnonymizationJobViewSet, basename='anonymization')
router.register('convert', ConversionJobViewSet, basename='conversion')
router.register('batch', BatchOperationViewSet, basename='batch')

urlpatterns = [
    # Upload endpoints
    path('upload/', DicomUploadView.as_view(), name='dicom-upload'),
    path('upload/medical/', MedicalImageUploadView.as_view(), name='medical-image-upload'),

    # DICOMweb QIDO-RS endpoints (OHIF compatible)
    path('dicom-web/studies', StudyListView.as_view(), name='dicomweb-studies'),
    path('dicom-web/studies/<str:study_uid>/series', SeriesListView.as_view(), name='dicomweb-series'),
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/instances', InstanceListView.as_view(), name='dicomweb-instances'),

    # DICOMweb WADO-RS endpoints (OHIF image retrieval)
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/instances/<str:sop_uid>/frames/<int:frame_number>',
         WADORSFrameRetrieveView.as_view(), name='wadors-frame'),
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/instances/<str:sop_uid>',
         WADORSInstanceRetrieveView.as_view(), name='wadors-instance'),

    # DICOMweb Metadata endpoints
    path('dicom-web/studies/<str:study_uid>/metadata',
         WADORSMetadataRetrieveView.as_view(), name='wadors-metadata-study'),
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/metadata',
         WADORSMetadataRetrieveView.as_view(), name='wadors-metadata-series'),
    path('dicom-web/studies/<str:study_uid>/series/<str:series_uid>/instances/<str:sop_uid>/metadata',
         WADORSMetadataRetrieveView.as_view(), name='wadors-metadata-instance'),

    # Study management
    path('studies/<str:study_uid>', DeleteStudyView.as_view(), name='delete-study'),

    # Storage quota
    path('storage/', StorageQuotaView.as_view(), name='storage-quota'),

    # Thumbnail endpoints
    path('series/<str:series_uid>/thumbnail/<str:size>/', SeriesThumbnailView.as_view(), name='series-thumbnail'),
    path('series/<str:series_uid>/generate-thumbnails/', GenerateThumbnailsView.as_view(), name='generate-thumbnails'),

    # Advanced search endpoints
    path('search/advanced/', AdvancedSearchView.as_view(), name='advanced-search'),
    path('search/saved/', SavedSearchListCreateView.as_view(), name='saved-searches'),
    path('search/saved/<int:search_id>/', SavedSearchDetailView.as_view(), name='saved-search-detail'),

    # Annotation endpoints
    path('images/<str:sop_uid>/annotations/', AnnotationListCreateView.as_view(), name='annotations-list'),
    path('annotations/<int:annotation_id>/', AnnotationDetailView.as_view(), name='annotation-detail'),

    # Tag editor endpoints
    path('images/<int:image_id>/tags/', DicomTagListView.as_view(), name='dicom-tag-list'),
    path('images/<int:image_id>/tags/update/', DicomTagUpdateView.as_view(), name='dicom-tag-update'),

    # Anonymization endpoints
    path('', include(router.urls)),
]
