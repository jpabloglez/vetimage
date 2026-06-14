"""
DICOM Images Views

API views for DICOM upload and DICOMweb-compatible queries.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.core.files.base import ContentFile
from django.conf import settings
from django.db import transaction, IntegrityError
from django.db import models as django_models
import pydicom
from datetime import datetime, date, time
import os
import logging

from .models import (
    MedicalStudy,
    MedicalSeries,
    MedicalImage,
    UserStorageQuota,
    SavedSearch,
    ImageAnnotation,
    AnnotationTemplate,
)
from .metadata_extractors import MetadataExtractorFactory
from .serializers import (
    DICOMwebStudySerializer,
    DICOMwebSeriesSerializer,
    DICOMwebInstanceSerializer,
    UserStorageQuotaSerializer,
    StudyListSerializer,
)
from .utils import (
    dicom_to_image,
    get_num_frames,
    extract_all_dicom_tags,
    normalize_text_for_search,
)
from django.http import HttpResponse, FileResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Upload DICOM files",
    description="""
    Upload one or more DICOM files for storage and processing.

    The endpoint:
    - Validates DICOM file format
    - Extracts metadata (patient info, study/series UIDs, image parameters)
    - Stores files organized by date
    - Updates user storage quota
    - Returns study/series/instance information

    Supports multipart/form-data with multiple files.
    """,
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'file': {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        }
    },
    responses={
        201: {
            'description': 'Files uploaded successfully',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'message': 'Uploaded 3 files successfully',
                        'studies': [
                            {
                                'study_instance_uid': '1.2.840.113619.2.55...',
                                'patient_name': 'DOE^JOHN',
                                'study_date': '2024-06-15',
                                'series_count': 1,
                                'instance_count': 3
                            }
                        ]
                    }
                }
            }
        },
        400: {'description': 'Invalid file format or missing required metadata'},
        401: {'description': 'Authentication required'},
        413: {'description': 'Upload would exceed storage quota'},
    },
    tags=['DICOM Upload'],
)
class DicomUploadView(APIView):
    """
    Upload DICOM files and parse metadata
    POST /api/dicom/upload/
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        Handle DICOM file upload with metadata extraction
        """
        # Check authentication (mock for now)
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get or create user storage quota
        quota, created = UserStorageQuota.objects.get_or_create(
            user=user,
            defaults={'quota_bytes': settings.USER_STORAGE_QUOTA}
        )

        # Get uploaded files
        uploaded_files = []
        for key in request.FILES:
            file_obj = request.FILES[key]
            uploaded_files.append(file_obj)

        if not uploaded_files:
            return Response(
                {'error': 'No files uploaded'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file extensions
        for file_obj in uploaded_files:
            ext = f".{file_obj.name.split('.')[-1]}"
            if ext.lower() not in settings.ALLOWED_DICOM_EXTENSIONS:
                return Response(
                    {'error': f'Invalid file type: {file_obj.name}. Only DICOM files allowed.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate file sizes
        total_size = sum(f.size for f in uploaded_files)
        if quota.used_bytes + total_size > quota.quota_bytes:
            return Response(
                {'error': f'Upload would exceed storage quota. Used: {quota.used_bytes}, Quota: {quota.quota_bytes}'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        # Process DICOM files
        uploaded_count = 0
        study_uid = None
        series_uid = None

        # Track studies, series, and instances created in THIS upload batch
        # This ensures files in one upload are grouped together, but different uploads create new records
        batch_studies = {}   # {study_instance_uid: MedicalStudy object}
        batch_series = {}    # {(series_instance_uid, study_id): MedicalSeries object}
        batch_instances = {} # {(sop_instance_uid, series_id): MedicalImage object}

        try:
            with transaction.atomic():
                for file_obj in uploaded_files:
                    # Read DICOM file
                    try:
                        dcm = pydicom.dcmread(file_obj, force=True)
                    except Exception as e:
                        logger.error(f"Failed to parse DICOM file {file_obj.name}: {e}")
                        return Response(
                            {'error': f'Failed to parse DICOM file {file_obj.name}: {str(e)}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # Extract metadata
                    study_instance_uid = str(getattr(dcm, 'StudyInstanceUID', None))
                    series_instance_uid = str(getattr(dcm, 'SeriesInstanceUID', None))
                    sop_instance_uid = str(getattr(dcm, 'SOPInstanceUID', None))

                    if not study_instance_uid or not series_instance_uid or not sop_instance_uid:
                        return Response(
                            {'error': f'DICOM file {file_obj.name} missing required UIDs'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # Get or create Study within THIS upload batch
                    # Check if we already created this study in this upload batch
                    if study_instance_uid in batch_studies:
                        study = batch_studies[study_instance_uid]
                        study_created = False
                    else:
                        # Create new study for this upload batch
                        study = MedicalStudy.objects.create(
                            study_instance_uid=study_instance_uid,
                            patient_id=str(getattr(dcm, 'PatientID', 'UNKNOWN')),
                            patient_name=str(getattr(dcm, 'PatientName', '')),
                            patient_birth_date=self._parse_dicom_date(getattr(dcm, 'PatientBirthDate', None)),
                            patient_sex=str(getattr(dcm, 'PatientSex', ''))[:1],
                            study_date=self._parse_dicom_date(getattr(dcm, 'StudyDate', None)),
                            study_time=self._parse_dicom_time(getattr(dcm, 'StudyTime', None)),
                            study_description=str(getattr(dcm, 'StudyDescription', '')),
                            accession_number=str(getattr(dcm, 'AccessionNumber', '')),
                            uploaded_by=user,
                        )
                        batch_studies[study_instance_uid] = study
                        study_created = True

                    # Get or create Series within THIS upload batch
                    # Use composite key (series_uid, study_id) to track series in this batch
                    series_key = (series_instance_uid, study.id)
                    if series_key in batch_series:
                        series = batch_series[series_key]
                        series_created = False
                    else:
                        # Create new series for this upload batch
                        series = MedicalSeries.objects.create(
                            series_instance_uid=series_instance_uid,
                            study=study,
                            series_number=int(getattr(dcm, 'SeriesNumber', 0)) if hasattr(dcm, 'SeriesNumber') else None,
                            series_description=str(getattr(dcm, 'SeriesDescription', '')),
                            modality=str(getattr(dcm, 'Modality', 'OT')),
                            body_part_examined=str(getattr(dcm, 'BodyPartExamined', '')),
                            series_date=self._parse_dicom_date(getattr(dcm, 'SeriesDate', None)),
                            series_time=self._parse_dicom_time(getattr(dcm, 'SeriesTime', None)),
                        )
                        batch_series[series_key] = series
                        series_created = True

                    # Note: Duplicate uploads are fully allowed
                    # Users can upload the same DICOM study multiple times
                    # Each upload is tracked separately by registry ID (primary key) and uploaded_at timestamp

                    # Get or create Instance within THIS upload batch
                    instance_key = (sop_instance_uid, series.id)
                    if instance_key in batch_instances:
                        # Skip duplicate instance in same upload batch
                        logger.info(f"Skipping duplicate instance {sop_instance_uid} in same upload batch")
                        continue

                    # Create MedicalImage
                    # Reset file pointer
                    file_obj.seek(0)

                    image = MedicalImage.objects.create(
                        series=series,
                        sop_instance_uid=sop_instance_uid,
                        sop_class_uid=str(getattr(dcm, 'SOPClassUID', '')),
                        instance_number=int(getattr(dcm, 'InstanceNumber', 0)) if hasattr(dcm, 'InstanceNumber') else None,
                        file=file_obj,
                        original_filename=file_obj.name,
                        file_size_bytes=file_obj.size,
                        rows=int(getattr(dcm, 'Rows', 0)) if hasattr(dcm, 'Rows') else None,
                        columns=int(getattr(dcm, 'Columns', 0)) if hasattr(dcm, 'Columns') else None,
                        number_of_frames=int(getattr(dcm, 'NumberOfFrames', 1)) if hasattr(dcm, 'NumberOfFrames') else 1,
                    )
                    batch_instances[instance_key] = image

                    # Extract ALL DICOM tags to JSON
                    dicom_tags = extract_all_dicom_tags(dcm, include_pixels=False)
                    image.dicom_tags = dicom_tags

                    # Extract technical parameters
                    if hasattr(dcm, 'PixelSpacing'):
                        try:
                            spacing = dcm.PixelSpacing
                            image.pixel_spacing_row = float(spacing[0])
                            image.pixel_spacing_column = float(spacing[1])
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to parse PixelSpacing: {e}")

                    if hasattr(dcm, 'SliceThickness'):
                        try:
                            image.slice_thickness = float(dcm.SliceThickness)
                        except ValueError as e:
                            logger.warning(f"Failed to parse SliceThickness: {e}")

                    if hasattr(dcm, 'SliceLocation'):
                        try:
                            image.slice_location = float(dcm.SliceLocation)
                        except ValueError as e:
                            logger.warning(f"Failed to parse SliceLocation: {e}")

                    # Extract window/level defaults
                    if hasattr(dcm, 'WindowCenter'):
                        try:
                            wc = dcm.WindowCenter
                            image.window_center = float(wc[0] if isinstance(wc, (list, tuple)) else wc)
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to parse WindowCenter: {e}")

                    if hasattr(dcm, 'WindowWidth'):
                        try:
                            ww = dcm.WindowWidth
                            image.window_width = float(ww[0] if isinstance(ww, (list, tuple)) else ww)
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to parse WindowWidth: {e}")

                    # Extract pixel value range (for CT Hounsfield units)
                    try:
                        if hasattr(dcm, 'pixel_array'):
                            pixel_array = dcm.pixel_array
                            image.min_pixel_value = int(pixel_array.min())
                            image.max_pixel_value = int(pixel_array.max())
                    except Exception as e:
                        logger.warning(f"Failed to extract pixel value range: {e}")

                    # Save image with all extracted metadata
                    image.save()

                    # Update series with DICOM tags and normalized fields (only on first image)
                    if not series.dicom_tags:
                        series.dicom_tags = dicom_tags
                        series.series_description_normalized = normalize_text_for_search(
                            series.series_description
                        )
                        series.save()

                    # Update study with DICOM tags and normalized fields (only on creation)
                    if study_created or not study.dicom_tags:
                        study.dicom_tags = dicom_tags
                        study.patient_name_normalized = normalize_text_for_search(
                            study.patient_name
                        )
                        study.study_description_normalized = normalize_text_for_search(
                            study.study_description
                        )
                        study.save()

                    # Mark series for thumbnail generation (lazy generation)
                    if series_created:
                        series.thumbnail_generation_status = 'pending'
                        series.save()

                    # Update study total size
                    study.total_size_bytes += file_obj.size
                    study.save()

                    uploaded_count += 1
                    study_uid = study_instance_uid
                    series_uid = series_instance_uid

                # Update user storage quota
                quota.update_usage()

        except Exception as e:
            logger.error(f"Error processing DICOM upload: {e}")
            return Response(
                {'error': f'Failed to process DICOM files: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'success': True,
            'message': f'Successfully uploaded {uploaded_count} DICOM file(s)',
            'uploaded_count': uploaded_count,
            'study_uid': study_uid,
            'series_uid': series_uid,
        }, status=status.HTTP_201_CREATED)

    def _parse_dicom_date(self, dicom_date):
        """Parse DICOM date (YYYYMMDD) to Python date"""
        if not dicom_date:
            return None
        try:
            date_str = str(dicom_date)
            if len(date_str) == 8:
                return datetime.strptime(date_str, '%Y%m%d').date()
        except Exception as e:
            logger.warning(f"Failed to parse DICOM date {dicom_date}: {e}")
        return None

    def _parse_dicom_time(self, dicom_time):
        """Parse DICOM time (HHMMSS.FFFFFF) to Python time"""
        if not dicom_time:
            return None
        try:
            time_str = str(dicom_time).split('.')[0]  # Remove fractional seconds
            if len(time_str) >= 6:
                return datetime.strptime(time_str[:6], '%H%M%S').time()
        except Exception as e:
            logger.warning(f"Failed to parse DICOM time {dicom_time}: {e}")
        return None


class StudyListView(APIView):
    """
    DICOMweb QIDO-RS compatible endpoint for querying studies
    GET /api/dicom/dicom-web/studies
    """

    def get(self, request):
        """
        Query studies with optional filters
        """
        # Check authentication
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get user's studies (user-scoped access)
        studies = MedicalStudy.objects.filter(uploaded_by=user).select_related('animal_patient')

        # Apply filters from query parameters
        patient_id = request.query_params.get('PatientID')
        study_date = request.query_params.get('StudyDate')
        modality = request.query_params.get('ModalitiesInStudy')

        if patient_id:
            studies = studies.filter(patient_id__icontains=patient_id)

        if study_date:
            # DICOM date format: YYYYMMDD
            try:
                parsed_date = datetime.strptime(study_date, '%Y%m%d').date()
                studies = studies.filter(study_date=parsed_date)
            except ValueError:
                pass

        if modality:
            # Filter by series modality
            studies = studies.filter(series__modality=modality).distinct()

        # Pagination
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))
        studies = studies[offset:offset + limit]

        # Serialize using DICOMweb format
        serializer = DICOMwebStudySerializer(studies, many=True)
        return Response(serializer.data)


class SeriesListView(APIView):
    """
    DICOMweb QIDO-RS compatible endpoint for querying series
    GET /api/dicom/dicom-web/studies/{study_uid}/series
    """

    def get(self, request, study_uid):
        """
        Query series for a specific study
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get study (ensure user owns it)
        # Note: With duplicate uploads allowed, we get the most recent study with this UID
        try:
            study = MedicalStudy.objects.filter(
                study_instance_uid=study_uid,
                uploaded_by=user
            ).order_by('-uploaded_at').first()

            if not study:
                return Response(
                    {'error': 'Study not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"Error fetching study: {e}")
            return Response(
                {'error': 'Failed to fetch study'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Get series for this study
        series = MedicalSeries.objects.filter(study=study)

        # Serialize using DICOMweb format
        serializer = DICOMwebSeriesSerializer(series, many=True)
        return Response(serializer.data)


class InstanceListView(APIView):
    """
    DICOMweb QIDO-RS compatible endpoint for querying instances
    GET /api/dicom/dicom-web/studies/{study_uid}/series/{series_uid}/instances
    """

    def get(self, request, study_uid, series_uid):
        """
        Query instances for a specific series
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get series (ensure user owns the parent study)
        # Note: With duplicate uploads allowed, we get the most recent series
        try:
            series = MedicalSeries.objects.select_related('study').filter(
                series_instance_uid=series_uid,
                study__study_instance_uid=study_uid,
                study__uploaded_by=user
            ).order_by('-study__uploaded_at', '-created_at').first()

            if not series:
                return Response(
                    {'error': 'Series not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"Error fetching series: {e}")
            return Response(
                {'error': 'Failed to fetch series'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Get instances for this series
        instances = MedicalImage.objects.filter(series=series)

        # Serialize using DICOMweb format
        serializer = DICOMwebInstanceSerializer(instances, many=True)
        return Response(serializer.data)


class StorageQuotaView(APIView):
    """
    Get user storage quota information
    GET /api/dicom/storage/
    """

    def get(self, request):
        """
        Get current user's storage quota and usage
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get or create quota
        quota, created = UserStorageQuota.objects.get_or_create(
            user=user,
            defaults={'quota_bytes': settings.USER_STORAGE_QUOTA}
        )

        # Update usage
        quota.update_usage()

        # Serialize
        serializer = UserStorageQuotaSerializer(quota)
        return Response(serializer.data)


@extend_schema(tags=['DICOM'])
class DeleteStudyView(APIView):
    """
    Delete a study and all associated data, or link it to an animal patient.
    DELETE /api/dicom/studies/{study_uid}
    PATCH  /api/dicom/studies/{study_uid}   body: {"animal_patient_id": <id|null>}
    """

    @extend_schema(
        summary='Link/unlink a study to an animal patient',
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[OpenApiExample('Link', value={'animal_patient_id': 12})],
    )
    def patch(self, request, study_uid):
        """
        Link (or unlink) a study to a veterinary AnimalPatient.

        Only animal patients within the requesting user's organization may be
        linked. Pass animal_patient_id=null to unlink.
        """
        from patients.models import AnimalPatient

        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            study = MedicalStudy.objects.get(
                study_instance_uid=study_uid,
                uploaded_by=user
            )
        except MedicalStudy.DoesNotExist:
            return Response(
                {'error': 'Study not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if 'animal_patient_id' not in request.data:
            return Response(
                {'error': 'animal_patient_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        animal_id = request.data.get('animal_patient_id')
        if animal_id is None:
            study.animal_patient = None
        else:
            from patients.views import get_or_create_organization
            org = get_or_create_organization(user)
            try:
                animal = AnimalPatient.objects.get(
                    id=animal_id,
                    owner__organization=org,
                )
            except AnimalPatient.DoesNotExist:
                return Response(
                    {'error': 'Animal patient not found in your organization'},
                    status=status.HTTP_404_NOT_FOUND
                )
            study.animal_patient = animal

        study.save(update_fields=['animal_patient', 'updated_at'])
        return Response(
            {
                'success': True,
                'study_instance_uid': study.study_instance_uid,
                'animal_patient_id': study.animal_patient_id,
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary='Delete a study (cascades to series/images)',
        responses={204: OpenApiTypes.NONE, 404: OpenApiTypes.OBJECT},
    )
    def delete(self, request, study_uid):
        """
        Delete a study (and cascade to series/images)
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get study (ensure user owns it)
        try:
            study = MedicalStudy.objects.get(
                study_instance_uid=study_uid,
                uploaded_by=user
            )
        except MedicalStudy.DoesNotExist:
            return Response(
                {'error': 'Study not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete the study (cascade will delete series and images)
        study.delete()

        # Update user storage quota
        quota, _ = UserStorageQuota.objects.get_or_create(
            user=user,
            defaults={'quota_bytes': settings.USER_STORAGE_QUOTA}
        )
        quota.update_usage()

        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Retrieve rendered image frame (WADO-RS)",
    description="""
    Retrieve a specific frame from a DICOM instance as a rendered JPEG image.
    Supports windowing parameters for adjusting image display.

    DICOMweb WADO-RS compliant endpoint.
    """,
    parameters=[
        OpenApiParameter(
            name='study_uid',
            type=str,
            location=OpenApiParameter.PATH,
            description='Study Instance UID'
        ),
        OpenApiParameter(
            name='series_uid',
            type=str,
            location=OpenApiParameter.PATH,
            description='Series Instance UID'
        ),
        OpenApiParameter(
            name='sop_uid',
            type=str,
            location=OpenApiParameter.PATH,
            description='SOP Instance UID'
        ),
        OpenApiParameter(
            name='frame_number',
            type=int,
            location=OpenApiParameter.PATH,
            description='Frame number (1-based)'
        ),
        OpenApiParameter(
            name='window_center',
            type=float,
            location=OpenApiParameter.QUERY,
            description='Window center for image rendering',
            required=False
        ),
        OpenApiParameter(
            name='window_width',
            type=float,
            location=OpenApiParameter.QUERY,
            description='Window width for image rendering',
            required=False
        ),
    ],
    responses={
        200: {
            'description': 'JPEG image',
            'content': {
                'image/jpeg': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        404: {'description': 'Image not found'},
        401: {'description': 'Authentication required'},
    },
    tags=['DICOMweb WADO-RS'],
)
class WADORSFrameRetrieveView(APIView):
    """
    WADO-RS Frame Retrieve Endpoint
    GET /api/dicom/dicom-web/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}/frames/{frame_number}

    Retrieves a single frame from a DICOM instance as JPEG or PNG.
    Supports window/level parameters for on-the-fly contrast adjustment.

    Query Parameters:
        - window_center: Window center (level) for windowing
        - window_width: Window width for windowing
        - format: Output format (jpeg or png, default: jpeg)

    Returns: Image in specified format
    """

    def get(self, request, study_uid, series_uid, sop_uid, frame_number):
        """
        Retrieve specific frame from DICOM instance
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get the instance (with access control check)
        # Note: With duplicate uploads allowed, we get the most recent instance
        try:
            instance = MedicalImage.objects.select_related(
                'series__study'
            ).filter(
                sop_instance_uid=sop_uid,
                series__series_instance_uid=series_uid,
                series__study__study_instance_uid=study_uid,
                series__study__uploaded_by=user
            ).order_by('-series__study__uploaded_at', '-uploaded_at').first()

            if not instance:
                return HttpResponse(
                    'Instance not found',
                    status=404,
                    content_type='text/plain'
                )
        except Exception as e:
            logger.error(f"Error fetching instance: {e}")
            return HttpResponse(
                'Failed to fetch instance',
                status=500,
                content_type='text/plain'
            )

        # Get query parameters
        window_center = request.query_params.get('windowCenter')
        window_width = request.query_params.get('windowWidth')
        output_format = request.query_params.get('format', 'jpeg').upper()

        # Convert to float if provided
        if window_center:
            try:
                window_center = float(window_center)
            except ValueError:
                window_center = None

        if window_width:
            try:
                window_width = float(window_width)
            except ValueError:
                window_width = None

        # Validate output format
        if output_format not in ['JPEG', 'PNG']:
            output_format = 'JPEG'

        # Load medical image file (DICOM or NIfTI)
        file_path = instance.file.path
        file_extension = os.path.splitext(file_path)[1].lower()

        # Check if this is a NIfTI file
        if file_extension in ['.nii', '.gz']:
            # Handle NIfTI file
            try:
                import nibabel as nib
                import numpy as np
                from PIL import Image
                from io import BytesIO

                # Load NIfTI file
                nifti_img = nib.load(file_path)
                data = nifti_img.get_fdata()

                # Validate frame number (NIfTI slices are typically along the 3rd axis)
                if len(data.shape) == 3:
                    num_frames = data.shape[2]
                    frame_idx = frame_number - 1

                    if frame_idx < 0 or frame_idx >= num_frames:
                        return HttpResponse(
                            f'Frame {frame_number} out of range (1-{num_frames})',
                            status=400,
                            content_type='text/plain'
                        )

                    # Extract the slice
                    slice_data = data[:, :, frame_idx]
                else:
                    # 2D image
                    slice_data = data

                # Normalize to 0-255 range
                slice_min = np.min(slice_data)
                slice_max = np.max(slice_data)
                if slice_max > slice_min:
                    normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
                else:
                    normalized = np.zeros_like(slice_data, dtype=np.uint8)

                # Apply windowing if provided
                if window_center is not None and window_width is not None:
                    # Convert window parameters to min/max values
                    window_min = window_center - (window_width / 2)
                    window_max = window_center + (window_width / 2)

                    # Re-normalize with windowing
                    windowed = np.clip(slice_data, window_min, window_max)
                    if window_max > window_min:
                        normalized = ((windowed - window_min) / (window_max - window_min) * 255).astype(np.uint8)

                # Create PIL Image (flip vertically for correct orientation)
                pil_image = Image.fromarray(np.flipud(normalized))

                # Convert to output format
                image_buffer = BytesIO()
                pil_image.save(image_buffer, format=output_format, quality=90 if output_format == 'JPEG' else None)
                image_buffer.seek(0)  # Reset buffer position for reading

            except Exception as e:
                logger.error(f"Failed to render NIfTI image: {e}")
                return HttpResponse(
                    f'Failed to render NIfTI image: {str(e)}',
                    status=500,
                    content_type='text/plain'
                )
        elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            # Handle standard image files (JPEG, PNG, etc.)
            try:
                from PIL import Image
                from io import BytesIO

                # Load image directly with PIL
                pil_image = Image.open(file_path)

                # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
                if pil_image.mode not in ['RGB', 'L']:
                    pil_image = pil_image.convert('RGB')

                # For standard images, frame_number should be 1 (single frame)
                if frame_number != 1:
                    return HttpResponse(
                        f'Frame {frame_number} out of range (only frame 1 available)',
                        status=400,
                        content_type='text/plain'
                    )

                # Convert to output format
                image_buffer = BytesIO()
                if pil_image.mode == 'L':
                    # Grayscale image - convert to RGB for JPEG output
                    if output_format == 'JPEG':
                        pil_image = pil_image.convert('RGB')
                pil_image.save(image_buffer, format=output_format, quality=90 if output_format == 'JPEG' else None)
                image_buffer.seek(0)

            except Exception as e:
                logger.error(f"Failed to render standard image: {e}")
                return HttpResponse(
                    f'Failed to render image: {str(e)}',
                    status=500,
                    content_type='text/plain'
                )
        else:
            # Handle DICOM file
            try:
                dcm = pydicom.dcmread(file_path)
            except Exception as e:
                logger.error(f"Failed to read DICOM file: {e}")
                return HttpResponse(
                    f'Failed to read DICOM file: {str(e)}',
                    status=500,
                    content_type='text/plain'
                )

            # Validate frame number
            num_frames = get_num_frames(dcm)
            frame_idx = frame_number - 1  # WADO-RS uses 1-based indexing

            if frame_idx < 0 or frame_idx >= num_frames:
                return HttpResponse(
                    f'Frame {frame_number} out of range (1-{num_frames})',
                    status=400,
                    content_type='text/plain'
                )

            # Convert DICOM to image
            try:
                image_buffer = dicom_to_image(
                    dcm,
                    frame_number=frame_idx,
                    window_center=window_center,
                    window_width=window_width,
                    output_format=output_format
                )
            except Exception as e:
                logger.error(f"Failed to convert DICOM to image: {e}")
                return HttpResponse(
                    f'Failed to render image: {str(e)}',
                    status=500,
                    content_type='text/plain'
                )

        # Return image
        content_type = f'image/{output_format.lower()}'
        return HttpResponse(
            image_buffer.getvalue(),
            content_type=content_type,
            headers={
                'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                'Content-Disposition': f'inline; filename="frame_{frame_number}.{output_format.lower()}"'
            }
        )


class WADORSInstanceRetrieveView(APIView):
    """
    WADO-RS Instance Retrieve Endpoint
    GET /api/dicom/dicom-web/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}

    Retrieves the full DICOM file.

    Returns: DICOM file (application/dicom)
    """

    def get(self, request, study_uid, series_uid, sop_uid):
        """
        Retrieve full DICOM instance
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return HttpResponse(
                'Authentication required',
                status=401,
                content_type='text/plain'
            )

        # Get the instance (with access control check)
        # Note: With duplicate uploads allowed, we get the most recent instance
        try:
            instance = MedicalImage.objects.select_related(
                'series__study'
            ).filter(
                sop_instance_uid=sop_uid,
                series__series_instance_uid=series_uid,
                series__study__study_instance_uid=study_uid,
                series__study__uploaded_by=user
            ).order_by('-series__study__uploaded_at', '-uploaded_at').first()

            if not instance:
                return HttpResponse(
                    'Instance not found',
                    status=404,
                    content_type='text/plain'
                )
        except Exception as e:
            logger.error(f"Error fetching instance: {e}")
            return HttpResponse(
                'Failed to fetch instance',
                status=500,
                content_type='text/plain'
            )

        # Return DICOM file
        try:
            response = FileResponse(
                instance.file.open('rb'),
                content_type='application/dicom'
            )
            response['Content-Disposition'] = f'attachment; filename="{instance.original_filename}"'
            response['Cache-Control'] = 'public, max-age=3600'
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve DICOM file: {e}")
            return HttpResponse(
                f'Failed to retrieve file: {str(e)}',
                status=500,
                content_type='text/plain'
            )


class WADORSMetadataRetrieveView(APIView):
    """
    WADO-RS Metadata Retrieve Endpoint
    GET /api/dicom/dicom-web/studies/{study_uid}/metadata
    GET /api/dicom/dicom-web/studies/{study_uid}/series/{series_uid}/metadata
    GET /api/dicom/dicom-web/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}/metadata

    Retrieves DICOM metadata in JSON format without pixel data.

    Returns: JSON array of DICOM metadata
    """

    def get(self, request, study_uid, series_uid=None, sop_uid=None):
        """
        Retrieve DICOM metadata for study, series, or instance
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        metadata_list = []

        if sop_uid:
            # Instance-level metadata
            # Note: With duplicate uploads allowed, we get the most recent instance
            try:
                instance = MedicalImage.objects.select_related(
                    'series__study'
                ).filter(
                    sop_instance_uid=sop_uid,
                    series__series_instance_uid=series_uid,
                    series__study__study_instance_uid=study_uid,
                    series__study__uploaded_by=user
                ).order_by('-series__study__uploaded_at', '-uploaded_at').first()

                if not instance:
                    return Response(
                        {'error': 'Instance not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                instances = [instance]
            except Exception as e:
                logger.error(f"Error fetching instance metadata: {e}")
                return Response(
                    {'error': 'Failed to fetch instance metadata'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        elif series_uid:
            # Series-level metadata (all instances in series)
            try:
                series_obj = MedicalSeries.objects.select_related('study').get(
                    series_instance_uid=series_uid,
                    study__study_instance_uid=study_uid,
                    study__uploaded_by=user
                )
                instances = MedicalImage.objects.filter(series=series_obj)
            except MedicalSeries.DoesNotExist:
                return Response(
                    {'error': 'Series not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        else:
            # Study-level metadata (all instances in study)
            try:
                study = MedicalStudy.objects.get(
                    study_instance_uid=study_uid,
                    uploaded_by=user
                )
                instances = MedicalImage.objects.filter(
                    series__study=study
                ).select_related('series')
            except MedicalStudy.DoesNotExist:
                return Response(
                    {'error': 'Study not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Extract metadata from each instance
        for instance in instances:
            try:
                dcm = pydicom.dcmread(instance.file.path, stop_before_pixels=True)
                # Convert to JSON (basic implementation)
                metadata = {
                    'SOPInstanceUID': str(dcm.SOPInstanceUID),
                    'SOPClassUID': str(dcm.SOPClassUID),
                    'StudyInstanceUID': str(dcm.StudyInstanceUID),
                    'SeriesInstanceUID': str(dcm.SeriesInstanceUID),
                    'Modality': str(getattr(dcm, 'Modality', '')),
                    'PatientID': str(getattr(dcm, 'PatientID', '')),
                    'PatientName': str(getattr(dcm, 'PatientName', '')),
                    'StudyDate': str(getattr(dcm, 'StudyDate', '')),
                    'StudyDescription': str(getattr(dcm, 'StudyDescription', '')),
                    'SeriesDescription': str(getattr(dcm, 'SeriesDescription', '')),
                    'Rows': int(getattr(dcm, 'Rows', 0)),
                    'Columns': int(getattr(dcm, 'Columns', 0)),
                    'NumberOfFrames': int(getattr(dcm, 'NumberOfFrames', 1)),
                }
                metadata_list.append(metadata)
            except Exception as e:
                logger.error(f"Failed to read metadata for instance {instance.sop_instance_uid}: {e}")
                continue

        return Response(metadata_list)


# ============================================================================
# Thumbnail API Endpoints
# ============================================================================

class SeriesThumbnailView(APIView):
    """
    GET /api/dicom/series/{series_uid}/thumbnail/{size}/
    Retrieve or generate series thumbnail (lazy generation)
    """

    def get(self, request, series_uid, size):
        """
        Get thumbnail for series (generate if needed)
        size: small | medium | large
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            series = MedicalSeries.objects.get(series_instance_uid=series_uid)
        except MedicalSeries.DoesNotExist:
            return Response(
                {'error': f'Series {series_uid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if series.study.uploaded_by != user:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate size
        if size not in ['small', 'medium', 'large']:
            return Response(
                {'error': 'Invalid size. Must be small, medium, or large'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get thumbnail field
        thumbnail_field = getattr(series, f'thumbnail_{size}')

        # Check if thumbnail exists
        if not thumbnail_field or not thumbnail_field.name:
            # Generate thumbnails if not exists
            from .utils import generate_series_thumbnails
            success = generate_series_thumbnails(series)

            if not success:
                return Response(
                    {'error': 'Failed to generate thumbnail'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Refresh thumbnail field
            series.refresh_from_db()
            thumbnail_field = getattr(series, f'thumbnail_{size}')

        # Return thumbnail file
        if thumbnail_field and thumbnail_field.name:
            return FileResponse(
                thumbnail_field.open('rb'),
                content_type='image/jpeg',
                as_attachment=False
            )
        else:
            return Response(
                {'error': 'Thumbnail not available'},
                status=status.HTTP_404_NOT_FOUND
            )


class GenerateThumbnailsView(APIView):
    """
    POST /api/dicom/series/{series_uid}/generate-thumbnails/
    Manually trigger thumbnail generation for a series
    """

    def post(self, request, series_uid):
        """
        Generate thumbnails for series
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            series = MedicalSeries.objects.get(series_instance_uid=series_uid)
        except MedicalSeries.DoesNotExist:
            return Response(
                {'error': f'Series {series_uid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if series.study.uploaded_by != user:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Generate thumbnails
        from .utils import generate_series_thumbnails
        success = generate_series_thumbnails(series)

        if success:
            return Response({
                'success': True,
                'message': 'Thumbnails generated successfully',
                'thumbnail_urls': {
                    'small': request.build_absolute_uri(series.thumbnail_small.url) if series.thumbnail_small else None,
                    'medium': request.build_absolute_uri(series.thumbnail_medium.url) if series.thumbnail_medium else None,
                    'large': request.build_absolute_uri(series.thumbnail_large.url) if series.thumbnail_large else None,
                }
            })
        else:
            return Response(
                {'error': 'Failed to generate thumbnails'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# Advanced Search Endpoints
# ============================================================================

@extend_schema(
    summary="Advanced DICOM study search",
    description="""
    Search DICOM studies using multiple filter criteria.

    Supports:
    - Text search on patient name, ID, study description
    - Date range filtering
    - Modality filtering (CT, MR, CR, etc.)
    - Body part filtering
    - Pagination
    """,
    request={
        'application/json': {
            'example': {
                'patient_name': 'john',
                'modality': ['CT', 'MR'],
                'date_from': '2024-01-01',
                'date_to': '2024-12-31',
                'limit': 50,
                'offset': 0
            }
        }
    },
    responses={
        200: {
            'description': 'Search results',
            'content': {
                'application/json': {
                    'example': {
                        'total': 150,
                        'limit': 50,
                        'offset': 0,
                        'results': [
                            {
                                'id': 1,
                                'study_instance_uid': '1.2.840...',
                                'patient_name': 'DOE^JOHN',
                                'study_date': '2024-06-15',
                                'study_description': 'CT CHEST',
                                'number_of_series': 3,
                                'number_of_instances': 120
                            }
                        ]
                    }
                }
            }
        },
        401: {'description': 'Authentication required'},
    },
    tags=['Search'],
)
class AdvancedSearchView(APIView):
    """
    POST /api/dicom/search/advanced/
    Advanced search with multiple filter criteria
    """

    def post(self, request):
        """
        Search studies with advanced filters
        Request body: {
            patient_name: str,
            patient_id: str,
            study_description: str,
            modality: [str],
            date_from: str (YYYY-MM-DD),
            date_to: str (YYYY-MM-DD),
            body_part: str,
            limit: int,
            offset: int
        }
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Get filter parameters
        patient_name = request.data.get('patient_name', '')
        patient_id = request.data.get('patient_id', '')
        study_description = request.data.get('study_description', '')
        modalities = request.data.get('modality', [])
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')
        body_part = request.data.get('body_part', '')
        limit = int(request.data.get('limit', 50))
        offset = int(request.data.get('offset', 0))

        # Build query
        from .utils import normalize_text_for_search
        queryset = MedicalStudy.objects.filter(uploaded_by=user)

        # Text search on normalized fields
        if patient_name:
            normalized_name = normalize_text_for_search(patient_name)
            queryset = queryset.filter(patient_name_normalized__icontains=normalized_name)

        if patient_id:
            queryset = queryset.filter(patient_id__icontains=patient_id)

        if study_description:
            normalized_desc = normalize_text_for_search(study_description)
            queryset = queryset.filter(study_description_normalized__icontains=normalized_desc)

        # Date range
        if date_from:
            queryset = queryset.filter(study_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(study_date__lte=date_to)

        # Modality filter (requires joining with series)
        if modalities and len(modalities) > 0:
            queryset = queryset.filter(series__modality__in=modalities).distinct()

        # Body part filter
        if body_part:
            queryset = queryset.filter(series__body_part_examined__icontains=body_part).distinct()

        # Get total count
        total = queryset.count()

        # Apply pagination
        queryset = queryset[offset:offset + limit]

        # Serialize results
        from .serializers import StudyListSerializer
        serializer = StudyListSerializer(queryset, many=True)

        return Response({
            'total': total,
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        })


class SavedSearchListCreateView(APIView):
    """
    GET/POST /api/dicom/search/saved/
    List user's saved searches or create new
    """

    def get(self, request):
        """
        List all saved searches for user
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        searches = SavedSearch.objects.filter(user=user)
        from .serializers import SavedSearchSerializer
        serializer = SavedSearchSerializer(searches, many=True)

        return Response(serializer.data)

    def post(self, request):
        """
        Create new saved search
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        from .serializers import SavedSearchSerializer
        serializer = SavedSearchSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SavedSearchDetailView(APIView):
    """
    GET/PUT/DELETE /api/dicom/search/saved/{search_id}/
    Retrieve, update, delete, or execute saved search
    """

    def get(self, request, search_id):
        """
        Get saved search details or execute it
        Query param: execute=true to run the search
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            saved_search = SavedSearch.objects.get(id=search_id, user=user)
        except SavedSearch.DoesNotExist:
            return Response(
                {'error': 'Saved search not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if we should execute the search
        execute = request.query_params.get('execute', 'false').lower() == 'true'

        if execute:
            # Update last_used_at and use_count
            from datetime import datetime
            saved_search.last_used_at = datetime.now()
            saved_search.use_count += 1
            saved_search.save()

            # Execute search using the saved filters
            # Reuse AdvancedSearchView logic
            search_view = AdvancedSearchView()
            request._full_data = saved_search.search_filters
            return search_view.post(request)
        else:
            # Just return search details
            from .serializers import SavedSearchSerializer
            serializer = SavedSearchSerializer(saved_search)
            return Response(serializer.data)

    def put(self, request, search_id):
        """
        Update saved search
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            saved_search = SavedSearch.objects.get(id=search_id, user=user)
        except SavedSearch.DoesNotExist:
            return Response(
                {'error': 'Saved search not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        from .serializers import SavedSearchSerializer
        serializer = SavedSearchSerializer(saved_search, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, search_id):
        """
        Delete saved search
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            saved_search = SavedSearch.objects.get(id=search_id, user=user)
        except SavedSearch.DoesNotExist:
            return Response(
                {'error': 'Saved search not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        saved_search.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Annotation Endpoints
# ============================================================================

@extend_schema(
    summary="List/Create image annotations",
    description="""
    Create annotations on DICOM images with automatic measurement calculations.

    Supported annotation types:
    - distance: 2-point line with length calculation
    - area: Polygon with area calculation
    - angle: 3-point angle measurement
    - text, arrow, rectangle, ellipse, line, roi

    Measurements are automatically calculated in mm (if pixel spacing available) or pixels.
    """,
    request={
        'application/json': {
            'example': {
                'annotation_type': 'distance',
                'frame_number': 0,
                'geometry_data': {
                    'points': [
                        {'x': 100, 'y': 150},
                        {'x': 200, 'y': 250}
                    ]
                },
                'label': 'Tumor diameter',
                'visibility': 'private'
            }
        }
    },
    responses={
        201: {
            'description': 'Annotation created with automatic measurements',
            'content': {
                'application/json': {
                    'example': {
                        'id': 1,
                        'annotation_type': 'distance',
                        'geometry_data': {
                            'points': [
                                {'x': 100, 'y': 150},
                                {'x': 200, 'y': 250}
                            ]
                        },
                        'measurement_value': 70.71,
                        'measurement_unit': 'mm',
                        'label': 'Tumor diameter'
                    }
                }
            }
        },
        400: {'description': 'Invalid geometry data'},
        401: {'description': 'Authentication required'},
    },
    tags=['Annotations'],
)
class AnnotationListCreateView(APIView):
    """
    GET/POST /api/dicom/images/{sop_uid}/annotations/
    List annotations for image or create new annotation
    """

    def get(self, request, sop_uid):
        """
        List all annotations for an image
        Query params: frame=N for multi-frame images
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            image = MedicalImage.objects.get(sop_instance_uid=sop_uid)
        except MedicalImage.DoesNotExist:
            return Response(
                {'error': f'Image {sop_uid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if image.series.study.uploaded_by != user:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get annotations for image
        annotations = ImageAnnotation.objects.filter(image=image)

        # Filter by frame if specified
        frame = request.query_params.get('frame')
        if frame is not None:
            annotations = annotations.filter(frame_number=int(frame))

        # Filter by visibility (private + shared + public for owner, shared + public for others)
        annotations = annotations.filter(
            django_models.Q(created_by=user) |  # User's own annotations (all visibility levels)
            django_models.Q(visibility__in=['shared', 'public'])  # Shared/public from others
        )

        from .serializers import ImageAnnotationSerializer
        serializer = ImageAnnotationSerializer(annotations, many=True)

        return Response(serializer.data)

    def post(self, request, sop_uid):
        """
        Create new annotation for image
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            image = MedicalImage.objects.get(sop_instance_uid=sop_uid)
        except MedicalImage.DoesNotExist:
            return Response(
                {'error': f'Image {sop_uid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check ownership
        if image.series.study.uploaded_by != user:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        from .serializers import ImageAnnotationSerializer
        serializer = ImageAnnotationSerializer(data=request.data)

        if serializer.is_valid():
            # Set image and created_by
            serializer.save(image=image, created_by=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnnotationDetailView(APIView):
    """
    GET/PUT/DELETE /api/dicom/annotations/{annotation_id}/
    Retrieve, update, or delete annotation
    """

    def get(self, request, annotation_id):
        """
        Get annotation details
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            annotation = ImageAnnotation.objects.get(id=annotation_id)
        except ImageAnnotation.DoesNotExist:
            return Response(
                {'error': 'Annotation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check access (owner or public/shared visibility)
        if annotation.created_by != user and annotation.visibility == 'private':
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        from .serializers import ImageAnnotationSerializer
        serializer = ImageAnnotationSerializer(annotation)

        return Response(serializer.data)

    def put(self, request, annotation_id):
        """
        Update annotation (only creator can update)
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            annotation = ImageAnnotation.objects.get(id=annotation_id)
        except ImageAnnotation.DoesNotExist:
            return Response(
                {'error': 'Annotation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only creator can update
        if annotation.created_by != user:
            return Response(
                {'error': 'Only the creator can update this annotation'},
                status=status.HTTP_403_FORBIDDEN
            )

        from .serializers import ImageAnnotationSerializer
        serializer = ImageAnnotationSerializer(annotation, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, annotation_id):
        """
        Delete annotation (only creator can delete)
        """
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            annotation = ImageAnnotation.objects.get(id=annotation_id)
        except ImageAnnotation.DoesNotExist:
            return Response(
                {'error': 'Annotation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only creator can delete
        if annotation.created_by != user:
            return Response(
                {'error': 'Only the creator can delete this annotation'},
                status=status.HTTP_403_FORBIDDEN
            )

        annotation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MedicalImageUploadView(APIView):
    """
    Upload medical images in multiple formats (DICOM, NIfTI, JPG/PNG) for AI analysis.

    POST /api/dicom/upload/medical/

    This endpoint is optimized for the analysis workflow and supports:
    - DICOM (.dcm, .dicom)
    - NIfTI (.nii, .nii.gz)
    - Standard images (.jpg, .jpeg, .png)

    Returns extracted metadata for model recommendation.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        Handle multi-format medical image upload with metadata extraction.

        Returns:
            - uploaded_images: List of uploaded image records with metadata
            - Each record includes extracted metadata for model recommendations
        """
        user = request.user

        # Get or create user storage quota
        quota, created = UserStorageQuota.objects.get_or_create(
            user=user,
            defaults={'quota_bytes': settings.USER_STORAGE_QUOTA}
        )

        # Get uploaded files
        uploaded_files = []
        for key in request.FILES:
            file_obj = request.FILES[key]
            uploaded_files.append(file_obj)

        if not uploaded_files:
            return Response(
                {'error': 'No files uploaded'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file extensions
        for file_obj in uploaded_files:
            filename_lower = file_obj.name.lower()

            # Check for .nii.gz first (multi-part extension)
            if filename_lower.endswith('.nii.gz'):
                ext = '.nii.gz'
            else:
                ext = f".{file_obj.name.split('.')[-1]}"

            if ext.lower() not in settings.ALLOWED_MEDICAL_IMAGE_EXTENSIONS:
                return Response(
                    {
                        'error': f'Invalid file type: {file_obj.name}',
                        'detail': f'Supported formats: {", ".join(settings.ALLOWED_MEDICAL_IMAGE_EXTENSIONS)}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate total file size
        total_size = sum(f.size for f in uploaded_files)
        for f in uploaded_files:
            if f.size > settings.MAX_UPLOAD_SIZE:
                return Response(
                    {
                        'error': f'File {f.name} exceeds maximum size of {settings.MAX_UPLOAD_SIZE} bytes'
                    },
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )

        # Check quota
        if quota.used_bytes + total_size > quota.quota_bytes:
            return Response(
                {
                    'error': 'Upload would exceed storage quota',
                    'used_bytes': quota.used_bytes,
                    'quota_bytes': quota.quota_bytes,
                    'upload_size': total_size
                },
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        # Process files
        uploaded_images = []

        try:
            with transaction.atomic():
                for file_obj in uploaded_files:
                    # Save file temporarily to extract metadata
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_obj.name) as tmp_file:
                        for chunk in file_obj.chunks():
                            tmp_file.write(chunk)
                        tmp_path = tmp_file.name

                    try:
                        # Extract metadata using appropriate extractor
                        metadata = MetadataExtractorFactory.extract_metadata(tmp_path)

                        # Handle DICOM files differently - preserve original UIDs
                        file_format = metadata['format']
                        modality = metadata.get('modality', 'UNKNOWN')

                        if metadata['format'] == 'dicom':
                            # CRITICAL: For DICOM, preserve original UIDs from DICOM tags
                            dicom_tags = metadata.get('all_tags', {})

                            # Extract DICOM UIDs (use original values, not synthetic)
                            study_uid = dicom_tags.get('0020000D', {}).get('value')  # Study Instance UID
                            series_uid = dicom_tags.get('0020000E', {}).get('value')  # Series Instance UID
                            sop_uid = dicom_tags.get('00080018', {}).get('value')  # SOP Instance UID

                            # Extract patient info
                            patient_id = dicom_tags.get('00100020', {}).get('value', f'USER-{user.id}')
                            patient_name = dicom_tags.get('00100010', {}).get('value', user.email)

                            # Extract study info
                            study_date_str = dicom_tags.get('00080020', {}).get('value')
                            if study_date_str:
                                try:
                                    study_date = datetime.strptime(study_date_str, '%Y%m%d').date()
                                except:
                                    study_date = date.today()
                            else:
                                study_date = date.today()

                            study_description = dicom_tags.get('00081030', {}).get('value', 'DICOM Study')
                            series_description = dicom_tags.get('0008103E', {}).get('value', 'DICOM Series')

                            # Create or get study with ORIGINAL UID
                            study, _ = MedicalStudy.objects.get_or_create(
                                study_instance_uid=study_uid,
                                defaults={
                                    'patient_id': patient_id,
                                    'patient_name': patient_name,
                                    'study_date': study_date,
                                    'study_description': study_description,
                                    'uploaded_by': user,
                                }
                            )

                            # Create or get series with ORIGINAL UID
                            series, _ = MedicalSeries.objects.get_or_create(
                                series_instance_uid=series_uid,
                                defaults={
                                    'study': study,
                                    'series_description': series_description,
                                    'modality': modality,
                                    'series_date': study_date,
                                }
                            )
                        else:
                            # For non-DICOM formats, use synthetic UIDs
                            study_uid = f"ANALYSIS-{user.id}-{file_format.upper()}-{datetime.now().strftime('%Y%m%d')}"
                            study, _ = MedicalStudy.objects.get_or_create(
                                study_instance_uid=study_uid,
                                defaults={
                                    'patient_id': f'USER-{user.id}',
                                    'patient_name': f'{user.email}',
                                    'study_date': date.today(),
                                    'study_description': f'{file_format.upper()} Analysis Images',
                                    'uploaded_by': user,
                                }
                            )

                            # Create series with synthetic UID
                            series_uid = f"{study_uid}-{modality}-{datetime.now().strftime('%H%M%S')}"
                            series, _ = MedicalSeries.objects.get_or_create(
                                series_instance_uid=series_uid,
                                defaults={
                                    'study': study,
                                    'series_description': f'{file_format.upper()} - {os.path.basename(file_obj.name)}',
                                    'modality': modality,
                                    'series_date': date.today(),
                                }
                            )

                            # Generate synthetic SOP Instance UID
                            import uuid
                            sop_uid = f"ANALYSIS-{uuid.uuid4()}"

                        # Create image record
                        # Reset file pointer
                        file_obj.seek(0)

                        dimensions = metadata.get('dimensions', {})

                        # Use get_or_create to handle duplicate uploads gracefully (idempotent)
                        image, created = MedicalImage.objects.get_or_create(
                            sop_instance_uid=sop_uid,
                            defaults={
                                'series': series,
                                'file': file_obj,
                                'original_filename': file_obj.name,
                                'file_size_bytes': file_obj.size,
                                'rows': dimensions.get('height'),
                                'columns': dimensions.get('width'),
                                'number_of_frames': dimensions.get('depth', 1),
                                'dicom_tags': metadata,  # Store all metadata in dicom_tags JSON field
                            }
                        )

                        # Update quota only if new image was created
                        if created:
                            quota.used_bytes += file_obj.size
                            quota.save()

                        uploaded_images.append({
                            'id': image.id,
                            'filename': file_obj.name,
                            'format': file_format,
                            'size_bytes': file_obj.size,
                            'metadata': metadata,
                            'study_id': study.id,
                            'series_id': series.id,
                            'created': created,  # Indicate if newly created or already existed
                        })

                    finally:
                        # Clean up temporary file
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

                logger.info(
                    f"User {user.id} uploaded {len(uploaded_images)} medical images "
                    f"({total_size} bytes)"
                )

                return Response(
                    {
                        'uploaded_images': uploaded_images,
                        'total_count': len(uploaded_images),
                        'total_size_bytes': total_size,
                        'quota_used_bytes': quota.used_bytes,
                        'quota_total_bytes': quota.quota_bytes,
                    },
                    status=status.HTTP_201_CREATED
                )

        except ValueError as e:
            # Metadata extraction error
            logger.error(f"Metadata extraction failed: {e}")
            return Response(
                {'error': f'Failed to process file: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Upload error: {e}", exc_info=True)
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ---------------------------------------------------------------------------
# Study sharing (StudyShareLink)
# ---------------------------------------------------------------------------

from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import StudyShareLink
from .serializers import StudyShareLinkSerializer


class StudyShareViewSet(viewsets.ModelViewSet):
    """Create and manage share links for DICOM studies."""
    serializer_class = StudyShareLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = getattr(self.request.user, 'userprofile', None)
        if profile is None or profile.organization is None:
            return StudyShareLink.objects.none()
        qs = StudyShareLink.objects.filter(
            study__uploaded_by__userprofile__organization=profile.organization
        ).select_related('study', 'created_by')
        study_uid = self.request.query_params.get('study')
        if study_uid:
            qs = qs.filter(study__study_instance_uid=study_uid)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PublicStudyWADOView(APIView):
    """
    Token-gated public DICOM metadata endpoint for shared studies.
    Returns basic study metadata; actual image bytes are served via OHIF/WADO-RS
    (the client uses the token to authenticate downstream requests).
    No authentication required — access is controlled solely by the unguessable token.
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        from django.utils import timezone
        try:
            link = StudyShareLink.objects.select_related('study').get(token=token)
        except StudyShareLink.DoesNotExist:
            return Response({'error': 'Invalid or expired share link.'}, status=status.HTTP_404_NOT_FOUND)

        if not link.is_valid():
            return Response({'error': 'This share link has expired or reached its access limit.'}, status=status.HTTP_403_FORBIDDEN)

        link.access_count += 1
        link.save(update_fields=['access_count'])

        study = link.study
        return Response({
            'study_instance_uid': study.study_instance_uid,
            'study_description': study.study_description,
            'study_date': study.study_date,
            'patient_id': study.patient_id,
            'modality': study.modality,
            'expires_at': link.expires_at,
            'accesses_remaining': (link.max_accesses - link.access_count) if link.max_accesses else None,
        })


class StudyCDExportView(APIView):
    """
    Export a study as a DICOM CD/USB ZIP (DICOMDIR layout when the instances
    are conformant; plain DICOM/ folder fallback otherwise).
    Org-scoped: the study must belong to the requesting user's organization.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, study_uid):
        from .models import MedicalStudy
        from .services.cd_export import build_cd_zip
        from patients.views import get_or_create_organization

        org = get_or_create_organization(request.user)
        try:
            study = MedicalStudy.objects.get(
                study_instance_uid=study_uid,
                uploaded_by__userprofile__organization=org,
            )
        except MedicalStudy.DoesNotExist:
            return Response({'error': 'Study not found.'}, status=status.HTTP_404_NOT_FOUND)

        zip_buffer = build_cd_zip(study)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = (
            f'attachment; filename="dicom_cd_{study_uid[-12:].replace(".", "_")}.zip"'
        )
        return response
