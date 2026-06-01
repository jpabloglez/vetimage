"""
Management command to register MIRAGE model in the AI Analysis system.

Usage:
    python manage.py register_mirage
    python manage.py register_mirage --update  # Update existing entry
"""

from django.core.management.base import BaseCommand
from ai_analysis.models import AIModel


class Command(BaseCommand):
    help = 'Register MIRAGE OCT analysis model in the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing MIRAGE model entry if it exists',
        )
        parser.add_argument(
            '--url',
            type=str,
            default='http://mirage-api-server:8000',
            help='MIRAGE service endpoint URL (default: http://mirage-api-server:8000)',
        )

    def handle(self, *args, **options):
        model_key = 'mirage-v1'
        update_existing = options['update']
        endpoint_url = options['url']

        # Check if model already exists
        existing_model = AIModel.objects.filter(key=model_key).first()

        if existing_model and not update_existing:
            self.stdout.write(
                self.style.WARNING(
                    f'MIRAGE model already registered (key={model_key}). '
                    'Use --update to update it.'
                )
            )
            return

        # Model configuration
        model_data = {
            'name': 'MIRAGE v1.0',
            'key': model_key,
            'description': (
                'MIRAGE (Medical Image Representation via Adversarial Gradient Estimation) '
                'is a foundation model for retinal OCT images. It supports feature extraction, '
                'segmentation, and classification tasks across multiple OCT modalities including '
                'B-scan, SLO, and layer segmentation maps.'
            ),
            'version': '1.0.0',
            'endpoint_url': endpoint_url,
            'connector_class': 'ai_analysis.connectors.mirage.MirageConnector',

            # Model metadata
            'model_type': 'other',  # Multi-purpose: segmentation, classification, feature extraction
            'supported_modalities': ['OCT', 'OPT'],  # Optical Coherence Tomography, Ophthalmic Photography

            # Required parameters schema
            'required_parameters': {
                'type': 'object',
                'properties': {
                    'task_type': {
                        'type': 'string',
                        'enum': ['feature_extraction', 'segmentation', 'classification'],
                        'description': 'Type of analysis to perform'
                    },
                    'modality': {
                        'type': 'string',
                        'enum': ['bscan', 'slo', 'bscanlayermap'],
                        'description': 'OCT image modality'
                    },
                },
                'required': ['task_type', 'modality']
            },

            # Default parameters
            'default_parameters': {
                'task_type': 'feature_extraction',
                'modality': 'bscan',
                'model_size': 'base',
                'output_destination': None  # Auto-generated if not provided
            },

            # Operational settings
            'timeout_seconds': 300,  # 5 minutes (OCT analysis is typically fast)
            'max_retries': 3,
            'retry_delay_seconds': 30,
            'is_active': True,

            # Open Medical AI Platform Metadata
            'authors': [
                {
                    'name': 'MIRAGE Research Team',
                    'affiliation': 'Medical Imaging Research Center',
                }
            ],
            'organization': 'Medical Imaging Research Center',
            'publication_title': 'MIRAGE: A Foundation Model for Retinal OCT Analysis',
            'tags': ['oct', 'retina', 'ophthalmology', 'foundation-model', 'deep-learning', 'pytorch'],
            'medical_domains': ['ophthalmology', 'retina'],
            'anatomical_regions': ['eye', 'retina', 'optic-nerve'],
            'use_cases': [
                'Diabetic retinopathy screening',
                'Macular degeneration detection',
                'Retinal layer segmentation',
                'Disease biomarker extraction'
            ],
            'limitations': (
                'Trained primarily on OCT images. '
                'May not generalize well to other imaging modalities. '
                'Requires images to be preprocessed to specific dimensions (512x512 for bscan/slo, 128x128 for layermap).'
            ),
        }

        if existing_model:
            # Update existing model
            for key, value in model_data.items():
                setattr(existing_model, key, value)
            existing_model.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated MIRAGE model (key={model_key}, endpoint={endpoint_url})'
                )
            )
        else:
            # Create new model
            AIModel.objects.create(**model_data)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully registered MIRAGE model (key={model_key}, endpoint={endpoint_url})'
                )
            )

        # Display usage instructions
        self.stdout.write('\nTo use the MIRAGE model:')
        self.stdout.write('1. Ensure MIRAGE service is running at: ' + endpoint_url)
        self.stdout.write('2. Create analysis tasks via API:')
        self.stdout.write('   POST /api/ai-analysis/tasks/')
        self.stdout.write('   {')
        self.stdout.write('     "model_key": "mirage-v1",')
        self.stdout.write('     "input_image_id": <image_id>,')
        self.stdout.write('     "parameters": {')
        self.stdout.write('       "task_type": "feature_extraction",')
        self.stdout.write('       "modality": "bscan",')
        self.stdout.write('       "model_size": "base"')
        self.stdout.write('     }')
        self.stdout.write('   }')
        self.stdout.write('')
