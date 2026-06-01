"""
DICOM Images Serializers

DRF serializers for DICOM data with DICOMweb-compatible output.
"""

from rest_framework import serializers
from .models import (
    MedicalStudy,
    MedicalSeries,
    MedicalImage,
    UserStorageQuota,
    SavedSearch,
    ImageAnnotation,
    AnnotationTemplate,
)


class MedicalImageSerializer(serializers.ModelSerializer):
    """
    Serializer for individual DICOM instances
    """
    class Meta:
        model = MedicalImage
        fields = [
            'id',
            'sop_instance_uid',
            'sop_class_uid',
            'instance_number',
            'file',
            'file_size_bytes',
            'original_filename',
            'rows',
            'columns',
            'number_of_frames',
            'uploaded_at',
        ]
        read_only_fields = ['id', 'uploaded_at']


class MedicalSeriesSerializer(serializers.ModelSerializer):
    """
    Serializer for DICOM series with nested images
    """
    images = MedicalImageSerializer(many=True, read_only=True)
    number_of_instances = serializers.ReadOnlyField()

    class Meta:
        model = MedicalSeries
        fields = [
            'id',
            'series_instance_uid',
            'series_number',
            'series_description',
            'modality',
            'body_part_examined',
            'series_date',
            'series_time',
            'number_of_instances',
            'images',
        ]
        read_only_fields = ['id']


class MedicalStudySerializer(serializers.ModelSerializer):
    """
    Serializer for DICOM studies with nested series
    """
    series = MedicalSeriesSerializer(many=True, read_only=True)
    number_of_series = serializers.ReadOnlyField()
    number_of_instances = serializers.ReadOnlyField()
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)

    class Meta:
        model = MedicalStudy
        fields = [
            'id',
            'study_instance_uid',
            'patient_id',
            'patient_name',
            'patient_birth_date',
            'patient_sex',
            'study_date',
            'study_time',
            'study_description',
            'accession_number',
            'uploaded_by_email',
            'uploaded_at',
            'total_size_bytes',
            'number_of_series',
            'number_of_instances',
            'series',
        ]
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by_email']


class StudyListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for study list (without nested data)
    """
    number_of_series = serializers.ReadOnlyField()
    number_of_instances = serializers.ReadOnlyField()

    class Meta:
        model = MedicalStudy
        fields = [
            'id',
            'study_instance_uid',
            'patient_id',
            'patient_name',
            'study_date',
            'study_description',
            'uploaded_at',
            'number_of_series',
            'number_of_instances',
        ]


class DICOMwebStudySerializer(serializers.Serializer):
    """
    Serializer for DICOMweb QIDO-RS study query response
    Follows DICOMweb JSON format
    """
    id = serializers.IntegerField(read_only=True)
    StudyInstanceUID = serializers.CharField(source='study_instance_uid')
    StudyDate = serializers.DateField(source='study_date', format='%Y%m%d', allow_null=True)
    StudyTime = serializers.TimeField(source='study_time', format='%H%M%S', allow_null=True, required=False)
    PatientID = serializers.CharField(source='patient_id')
    PatientName = serializers.CharField(source='patient_name', allow_blank=True)
    PatientBirthDate = serializers.DateField(source='patient_birth_date', format='%Y%m%d', allow_null=True, required=False)
    PatientSex = serializers.CharField(source='patient_sex', allow_blank=True, required=False)
    StudyDescription = serializers.CharField(source='study_description', allow_blank=True, required=False)
    AccessionNumber = serializers.CharField(source='accession_number', allow_blank=True, required=False)
    NumberOfStudyRelatedSeries = serializers.IntegerField(source='number_of_series', read_only=True)
    NumberOfStudyRelatedInstances = serializers.IntegerField(source='number_of_instances', read_only=True)


class DICOMwebSeriesSerializer(serializers.Serializer):
    """
    Serializer for DICOMweb QIDO-RS series query response
    """
    SeriesInstanceUID = serializers.CharField(source='series_instance_uid')
    SeriesNumber = serializers.IntegerField(source='series_number', allow_null=True)
    SeriesDescription = serializers.CharField(source='series_description', allow_blank=True)
    Modality = serializers.CharField(source='modality')
    SeriesDate = serializers.DateField(source='series_date', format='%Y%m%d', allow_null=True, required=False)
    SeriesTime = serializers.TimeField(source='series_time', format='%H%M%S', allow_null=True, required=False)
    NumberOfSeriesRelatedInstances = serializers.IntegerField(source='number_of_instances', read_only=True)


class DICOMwebInstanceSerializer(serializers.Serializer):
    """
    Serializer for DICOMweb QIDO-RS instance query response
    """
    SOPInstanceUID = serializers.CharField(source='sop_instance_uid')
    SOPClassUID = serializers.CharField(source='sop_class_uid')
    InstanceNumber = serializers.IntegerField(source='instance_number', allow_null=True)
    Rows = serializers.IntegerField(source='rows', allow_null=True, required=False)
    Columns = serializers.IntegerField(source='columns', allow_null=True, required=False)
    NumberOfFrames = serializers.IntegerField(source='number_of_frames', required=False)


class UserStorageQuotaSerializer(serializers.ModelSerializer):
    """
    Serializer for user storage quota information
    """
    remaining_bytes = serializers.ReadOnlyField()
    usage_percentage = serializers.ReadOnlyField()
    is_over_quota = serializers.ReadOnlyField()

    class Meta:
        model = UserStorageQuota
        fields = [
            'used_bytes',
            'quota_bytes',
            'remaining_bytes',
            'usage_percentage',
            'is_over_quota',
            'last_updated',
        ]
        read_only_fields = ['last_updated']


class DicomUploadSerializer(serializers.Serializer):
    """
    Serializer for validating DICOM file uploads
    """
    files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False),
        allow_empty=False,
        help_text="List of DICOM files to upload"
    )

    def validate_files(self, value):
        """
        Validate that uploaded files are valid DICOM files
        """
        from django.conf import settings

        for file in value:
            # Check file extension
            ext = f".{file.name.split('.')[-1]}"
            if ext.lower() not in settings.ALLOWED_DICOM_EXTENSIONS:
                raise serializers.ValidationError(
                    f"File {file.name} is not a DICOM file. Allowed extensions: {settings.ALLOWED_DICOM_EXTENSIONS}"
                )

            # Check file size
            if file.size > settings.MAX_UPLOAD_SIZE:
                raise serializers.ValidationError(
                    f"File {file.name} exceeds maximum size of {settings.MAX_UPLOAD_SIZE} bytes"
                )

        return value


class SavedSearchSerializer(serializers.ModelSerializer):
    """
    Serializer for saved search queries
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = SavedSearch
        fields = [
            'id',
            'name',
            'description',
            'search_filters',
            'created_at',
            'last_used_at',
            'use_count',
            'user_email',
        ]
        read_only_fields = ['id', 'created_at', 'last_used_at', 'use_count', 'user_email']

    def validate_search_filters(self, value):
        """
        Validate that search_filters is a valid dictionary
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("search_filters must be a dictionary")
        return value


class ImageAnnotationSerializer(serializers.ModelSerializer):
    """
    Serializer for image annotations with automatic measurement calculations
    """
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    image_sop_uid = serializers.CharField(source='image.sop_instance_uid', read_only=True)

    class Meta:
        model = ImageAnnotation
        fields = [
            'id',
            'image',
            'image_sop_uid',
            'annotation_type',
            'frame_number',
            'geometry_data',
            'measurement_value',
            'measurement_unit',
            'label',
            'description',
            'visibility',
            'created_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'image',
            'created_at',
            'updated_at',
            'created_by_email',
            'image_sop_uid',
            'measurement_value',
            'measurement_unit',
        ]

    def validate_geometry_data(self, value):
        """
        Validate that geometry_data is appropriate for the annotation type
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("geometry_data must be a dictionary")
        return value

    def validate_annotation_type(self, value):
        """
        Validate annotation type
        """
        valid_types = [choice[0] for choice in ImageAnnotation.ANNOTATION_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid annotation type. Must be one of: {', '.join(valid_types)}"
            )
        return value

    def create(self, validated_data):
        """
        Create annotation with automatic measurement calculation
        """
        from .utils import (
            calculate_distance_measurement,
            calculate_area_measurement,
            calculate_angle_measurement,
        )

        annotation = super().create(validated_data)
        annotation_type = annotation.annotation_type
        geometry_data = annotation.geometry_data

        # Calculate measurements based on annotation type
        try:
            # Get pixel spacing from image
            pixel_spacing = None
            if annotation.image.pixel_spacing_row and annotation.image.pixel_spacing_column:
                pixel_spacing = (
                    annotation.image.pixel_spacing_row,
                    annotation.image.pixel_spacing_column
                )

            if annotation_type == 'distance':
                # Expecting geometry_data with 'points' array of 2 points
                if 'points' in geometry_data and len(geometry_data['points']) == 2:
                    result = calculate_distance_measurement(
                        geometry_data['points'][0],
                        geometry_data['points'][1],
                        pixel_spacing
                    )
                    annotation.measurement_value = result.get('length_mm') or result.get('length_pixels')
                    annotation.measurement_unit = result['unit']

            elif annotation_type == 'area':
                # Expecting geometry_data with 'points' array (polygon)
                if 'points' in geometry_data:
                    result = calculate_area_measurement(
                        geometry_data['points'],
                        pixel_spacing
                    )
                    annotation.measurement_value = result.get('area_mm2') or result.get('area_pixels')
                    annotation.measurement_unit = result['unit']

            elif annotation_type == 'angle':
                # Expecting geometry_data with 'points' array of 3 points
                if 'points' in geometry_data and len(geometry_data['points']) == 3:
                    result = calculate_angle_measurement(geometry_data['points'])
                    annotation.measurement_value = result['angle_degrees']
                    annotation.measurement_unit = 'degrees'

            annotation.save()

        except Exception as e:
            # Log error but don't fail annotation creation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to calculate measurement for annotation {annotation.id}: {e}")

        return annotation

    def update(self, instance, validated_data):
        """
        Update annotation and recalculate measurements if geometry changed
        """
        from .utils import (
            calculate_distance_measurement,
            calculate_area_measurement,
            calculate_angle_measurement,
        )

        # Check if geometry_data changed
        geometry_changed = 'geometry_data' in validated_data

        # Update instance
        instance = super().update(instance, validated_data)

        # Recalculate measurements if geometry changed
        if geometry_changed:
            try:
                pixel_spacing = None
                if instance.image.pixel_spacing_row and instance.image.pixel_spacing_column:
                    pixel_spacing = (
                        instance.image.pixel_spacing_row,
                        instance.image.pixel_spacing_column
                    )

                if instance.annotation_type == 'distance':
                    if 'points' in instance.geometry_data and len(instance.geometry_data['points']) == 2:
                        result = calculate_distance_measurement(
                            instance.geometry_data['points'][0],
                            instance.geometry_data['points'][1],
                            pixel_spacing
                        )
                        instance.measurement_value = result.get('length_mm') or result.get('length_pixels')
                        instance.measurement_unit = result['unit']

                elif instance.annotation_type == 'area':
                    if 'points' in instance.geometry_data:
                        result = calculate_area_measurement(
                            instance.geometry_data['points'],
                            pixel_spacing
                        )
                        instance.measurement_value = result.get('area_mm2') or result.get('area_pixels')
                        instance.measurement_unit = result['unit']

                elif instance.annotation_type == 'angle':
                    if 'points' in instance.geometry_data and len(instance.geometry_data['points']) == 3:
                        result = calculate_angle_measurement(instance.geometry_data['points'])
                        instance.measurement_value = result['angle_degrees']
                        instance.measurement_unit = 'degrees'

                instance.save()

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to recalculate measurement for annotation {instance.id}: {e}")

        return instance


class AnnotationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for annotation templates
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AnnotationTemplate
        fields = [
            'id',
            'name',
            'annotation_type',
            'default_properties',
            'created_at',
            'user_email',
        ]
        read_only_fields = ['id', 'created_at', 'user_email']

    def validate_default_properties(self, value):
        """
        Validate that default_properties is a valid dictionary
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("default_properties must be a dictionary")
        return value
