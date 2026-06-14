"""
DRF Serializers for AI Analysis API

This module defines Django REST Framework serializers for:
- AIModel: Registry of available AI models
- AnalysisTask: Task creation and status monitoring
"""

from rest_framework import serializers
from .models import AIModel, AnalysisTask
from dicom_images.serializers import MedicalImageSerializer


class AIModelSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for AIModel with all metadata.

    Used for detailed model views (model card page).
    Includes all fields: technical config, publications, licensing, performance, etc.
    """

    class Meta:
        model = AIModel
        fields = [
            # Core Identity
            'key',
            'name',
            'description',
            'version',

            # Technical Configuration
            'model_type',
            'supported_modalities',
            'required_parameters',
            'default_parameters',
            'timeout_seconds',
            'is_active',

            # Authors & Attribution
            'authors',
            'organization',

            # Publications & References
            'publication_title',
            'publication_journal',
            'publication_year',
            'publication_doi',
            'publication_url',
            'citation',

            # Code & Resources
            'github_url',
            'paper_url',
            'demo_url',
            'model_card_url',

            # Licensing
            'license_name',
            'license_url',

            # Model Characteristics
            'tags',
            'medical_domains',
            'anatomical_regions',
            'supported_species',

            # Performance Metrics
            'performance_metrics',
            'validation_dataset',
            'training_dataset',

            # Use Cases & Examples
            'use_cases',
            'limitations',
            'example_images',

            # Community & Support
            'documentation_url',
            'support_url',
            'homepage_url',

            # Statistics
            'download_count',
            'rating',

            # Connector Configuration
            'metadata',

            # Data Governance
            'requires_anonymization',

            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class AIModelListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing models — includes all fields needed by ModelCard.
    """

    class Meta:
        model = AIModel
        fields = [
            'key', 'name', 'model_type', 'version', 'is_active',
            'description', 'organization',
            'supported_modalities', 'anatomical_regions', 'medical_domains',
            'supported_species',
            'tags', 'performance_metrics', 'license_name', 'download_count',
            'required_parameters', 'default_parameters',
            'metadata', 'requires_anonymization',
        ]
        read_only_fields = fields


class CreateTaskSerializer(serializers.Serializer):
    """
    Serializer for creating new analysis tasks.

    Validates:
    - model_key exists and is active
    - input_image_id exists and belongs to user
    - additional image IDs in parameters (for multi-image models like PICAI)
    - parameters are valid JSON
    """

    model_key = serializers.CharField(
        max_length=50,
        help_text="Key of the AI model to use (e.g., 'mirage-v1')"
    )
    input_image_id = serializers.IntegerField(
        help_text="ID of the primary input image (e.g., T2W for PICAI)"
    )
    parameters = serializers.JSONField(
        default=dict,
        help_text="Model-specific parameters (for multi-image models, include adc_image_id, hbv_image_id, etc.)"
    )
    priority = serializers.ChoiceField(
        choices=['routine', 'urgent', 'stat'],
        default='routine',
        required=False,
        help_text="Triage priority (routine / urgent / stat)"
    )

    def validate_model_key(self, value):
        """Validate that model exists and is active"""
        try:
            AIModel.objects.get(key=value, is_active=True)
        except AIModel.DoesNotExist:
            raise serializers.ValidationError(
                f"AI model '{value}' not found or is inactive"
            )
        return value

    def validate_input_image_id(self, value):
        """Validate that image exists (authorization check happens in view)"""
        from dicom_images.models import MedicalImage
        try:
            MedicalImage.objects.get(id=value)
        except MedicalImage.DoesNotExist:
            raise serializers.ValidationError(
                f"Medical image with ID {value} not found"
            )
        return value

    def validate(self, data):
        """Validate additional image IDs, modality compatibility, and required parameters"""
        from dicom_images.models import MedicalImage
        from ai_analysis.services.model_recommender import ModelRecommender

        parameters = data.get('parameters', {})

        # Check for additional image IDs (e.g., adc_image_id, hbv_image_id for PICAI)
        image_id_fields = ['adc_image_id', 'hbv_image_id', 't2_image_id']

        for field in image_id_fields:
            if field in parameters:
                image_id = parameters[field]
                try:
                    MedicalImage.objects.get(id=image_id)
                except MedicalImage.DoesNotExist:
                    raise serializers.ValidationError({
                        'parameters': {field: f"Medical image with ID {image_id} not found"}
                    })

        # --- Modality compatibility check ---
        model = AIModel.objects.get(key=data['model_key'], is_active=True)
        image = MedicalImage.objects.get(id=data['input_image_id'])
        image_modality = image.series.modality

        supported = model.supported_modalities or []
        if supported and image_modality:
            exact_match = any(
                image_modality.upper() == mod.upper() for mod in supported
            )
            partial_match = any(
                ModelRecommender._is_partial_modality_match(image_modality, mod)
                for mod in supported
            )
            if not exact_match and not partial_match:
                data['_modality_warning'] = (
                    f"Image modality '{image_modality}' may not be compatible with "
                    f"model '{model.name}'. Supported modalities: {', '.join(supported)}"
                )

        # --- Enforce required parameters (e.g., adc_image_id for PICAI) ---
        required_params = model.required_parameters or {}
        for param_name, schema in required_params.items():
            if isinstance(schema, dict) and schema.get('required') and param_name not in parameters:
                raise serializers.ValidationError({
                    'parameters': {
                        param_name: f"Parameter '{param_name}' is required for model '{model.name}'"
                    }
                })

        return data


class AnalysisTaskSerializer(serializers.ModelSerializer):
    """
    Full serializer for AnalysisTask with nested relationships.

    Includes:
    - Model details
    - Input image details
    - Processing duration calculation
    - All status and timing fields
    """

    model = AIModelListSerializer(read_only=True)
    input_image = MedicalImageSerializer(read_only=True)
    processing_duration = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisTask
        fields = [
            'id',
            'model',
            'input_image',
            'status',
            'priority',
            'parameters',
            'created_at',
            'dispatched_at',
            'started_processing_at',
            'completed_at',
            'processing_duration',
            'total_duration',
            'result_file_path',
            'result_metadata',
            'error_message',
            'retry_count',
        ]
        read_only_fields = fields

    def get_processing_duration(self, obj) -> float:
        """Calculate time spent in AI processing (seconds)"""
        return obj.processing_duration

    def get_total_duration(self, obj) -> float:
        """Calculate total time from creation to completion (seconds)"""
        return obj.total_duration


class AnalysisTaskListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing tasks.
    Used in list views to reduce payload size.
    """

    model_name = serializers.CharField(source='model.name', read_only=True)
    model_key = serializers.CharField(source='model.key', read_only=True)

    class Meta:
        model = AnalysisTask
        fields = [
            'id',
            'model_key',
            'model_name',
            'status',
            'priority',
            'created_at',
            'completed_at',
            'error_message',
        ]
        read_only_fields = fields


class AnalysisTaskMonitorSerializer(serializers.ModelSerializer):
    """
    Serializer for Monitor page with privacy-aware colleague information.

    Conditionally includes user details based on is_sharing_jobs_with_colleagues.
    Shows processing duration and lightweight model info.
    """

    model_key = serializers.CharField(source='model.key', read_only=True)
    model_name = serializers.CharField(source='model.name', read_only=True)
    processing_duration = serializers.SerializerMethodField()

    # Conditional fields (only if sharing enabled or own task)
    created_by_name = serializers.SerializerMethodField()
    created_by_department = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisTask
        fields = [
            'id',
            'model_key',
            'model_name',
            'status',
            'created_at',
            'completed_at',
            'processing_duration',
            'created_by_name',
            'created_by_department',
            'parameters',
            'error_message',
            'result_file_path',
            'result_metadata',
        ]
        read_only_fields = fields

    def get_processing_duration(self, obj) -> float:
        """Calculate time spent in AI processing (seconds)"""
        return obj.processing_duration

    def get_created_by_name(self, obj):
        """Return user name only if sharing enabled or own task"""
        request = self.context.get('request')

        # If it's the user's own task, show "You"
        if request and obj.created_by_id == request.user.id:
            return "You"

        # Check if user is sharing jobs with colleagues
        try:
            profile = obj.created_by.userprofile
            if profile.is_sharing_jobs_with_colleagues:
                return f"{profile.first_name} {profile.last_name}"
        except Exception:
            pass

        # Default: don't expose private user
        return "Private"

    def get_created_by_department(self, obj):
        """Return department only if sharing enabled"""
        request = self.context.get('request')

        # If it's the user's own task, show their department
        if request and obj.created_by_id == request.user.id:
            try:
                return obj.created_by.userprofile.department
            except Exception:
                return None

        # Check if user is sharing jobs
        try:
            profile = obj.created_by.userprofile
            if profile.is_sharing_jobs_with_colleagues:
                return profile.department
        except Exception:
            pass

        return None


class WebhookPayloadSerializer(serializers.Serializer):
    """
    Serializer for validating incoming webhook payloads.
    """

    status = serializers.ChoiceField(
        choices=['PROCESSING', 'COMPLETED', 'FAILED'],
        help_text="New status of the task"
    )
    webhook_secret = serializers.CharField(
        max_length=64,
        help_text="Secret token for authentication"
    )
    result_file_path = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Path to result file (for COMPLETED status)"
    )
    metadata = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Additional metadata from AI service"
    )
    error_message = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Error description (for FAILED status)"
    )

    def validate(self, data):
        """
        Cross-field validation based on status.
        """
        status = data.get('status')

        # COMPLETED should have result_file_path
        if status == 'COMPLETED' and not data.get('result_file_path'):
            # Warning but not blocking
            pass

        # FAILED should have error_message
        if status == 'FAILED' and not data.get('error_message'):
            # Provide default
            data['error_message'] = 'Unknown error from AI service'

        return data
