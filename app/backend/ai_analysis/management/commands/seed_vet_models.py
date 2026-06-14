"""
Management command to seed VETERINARY AI model catalog entries.

Usage:
    python manage.py seed_vet_models            # seed vet models, hide human ones
    python manage.py seed_vet_models --keep-human   # seed vet models, leave human active

VetImage was forked from a human-imaging platform whose default models all
target human anatomy (retina, prostate, human chest/brain). This command:

  1. Deactivates those human-only models (is_active=False) so they no longer
     appear in the registry — the connector framework is preserved, nothing is
     deleted.
  2. Seeds veterinary-relevant catalog entries with HONEST metadata: supported
     species, version, sensitivity AND specificity (or an explicit
     "pending validation"), datasets, and limitations.

Per ACVR/ECVDI guidance and our clinical-alignment report, these are clearly
labelled decision-support / experimental tools — not validated diagnostic
devices. See docs/VETERINARY_ALIGNMENT_REPORT.md.
"""

from django.core.management.base import BaseCommand
from ai_analysis.models import AIModel

# Human-only models inherited from the upstream platform.
HUMAN_MODEL_KEYS = [
    'mirage-v1',      # retinal OCT/SLO
    'picai-v1',       # human prostate MRI
    'chexnet-v1',     # human chest X-ray
    'fastsurfer-v2',  # human brain MRI
    'stunet-s-v1', 'stunet-b-v1', 'stunet-l-v1',  # human CT segmentation
    'misfm-v1',       # human CT/MRI segmentation
]

# Veterinary catalog entries. These are honest placeholders: where no validated
# performance exists yet, performance_metrics says so explicitly rather than
# inventing numbers. `metadata.experimental` flags catalog-only entries.
VET_MODELS = [
    {
        'key': 'vet-thorax-cr-v1',
        'defaults': {
            'name': 'Canine/Feline Thoracic Radiograph Screening',
            'description': (
                'Decision-support screening for common thoracic radiographic '
                'findings in dogs and cats (e.g. cardiomegaly, pulmonary '
                'patterns, pleural effusion, pneumothorax). Draft findings only '
                '— a veterinarian must review and approve every result.'
            ),
            'version': '0.1.0-experimental',
            'connector_class': 'ai_analysis.connectors.vet_thorax.VetThoraxConnector',
            'endpoint_url': 'http://vet-thorax-service:8000',
            'model_type': 'classification',
            'supported_modalities': ['CR', 'DX'],
            'supported_species': ['canine', 'feline'],
            'medical_domains': ['radiology', 'cardiology', 'pulmonology'],
            'anatomical_regions': ['thorax', 'heart', 'lung'],
            'is_active': True,
            'use_orchestrator': False,
            'requires_anonymization': False,
            'organization': 'VetImage (experimental)',
            'performance_metrics': {'status': 'pending external validation'},
            'validation_dataset': 'Not yet externally validated',
            'training_dataset': 'Internal canine/feline thoracic radiographs (placeholder)',
            'limitations': (
                'EXPERIMENTAL. Not externally validated; no published sensitivity/'
                'specificity. Commercial veterinary thoracic AI has shown LOW '
                'sensitivity on complex cases (≈0.44) — a normal result does NOT '
                'rule out disease. Use only as a fallible second reader under '
                'veterinarian supervision. Not a medical device; not FDA-cleared.'
            ),
            'use_cases': [
                'Triage flagging of possible cardiomegaly / effusion',
                'Second-reader support for general practitioners',
            ],
            'tags': ['veterinary', 'thorax', 'canine', 'feline', 'experimental'],
            'metadata': {'experimental': True, 'human_in_the_loop': True},
        },
    },
    {
        'key': 'vet-vhs-v1',
        'defaults': {
            'name': 'Vertebral Heart Score (VHS) Assistant',
            'description': (
                'Computes the Vertebral Heart Score (and VLAS) from lateral '
                'thoracic radiographs by proposing cardiac/vertebral landmarks. '
                'A measurement aid — caliper points are veterinarian-editable and '
                'the final value is confirmed by the clinician.'
            ),
            'version': '0.1.0-experimental',
            'connector_class': 'ai_analysis.connectors.chexnet.CheXNetConnector',
            'model_type': 'detection',
            'supported_modalities': ['CR', 'DX'],
            'supported_species': ['canine', 'feline'],
            'medical_domains': ['cardiology', 'radiology'],
            'anatomical_regions': ['thorax', 'heart', 'spine'],
            'is_active': True,
            'use_orchestrator': False,
            'requires_anonymization': False,
            'organization': 'VetImage (experimental)',
            'performance_metrics': {'metric': 'landmark MAE', 'status': 'pending validation'},
            'validation_dataset': 'Not yet externally validated',
            'training_dataset': 'Internal lateral thoracic radiographs (placeholder)',
            'limitations': (
                'EXPERIMENTAL measurement aid. Landmark predictions must be '
                'reviewed and corrected by the veterinarian. VHS reference ranges '
                'are breed-dependent; interpret with clinical context. Not a '
                'medical device; not FDA-cleared.'
            ),
            'use_cases': [
                'Cardiomegaly screening via VHS',
                'Longitudinal VHS trend tracking per patient',
            ],
            'tags': ['veterinary', 'vhs', 'cardiology', 'measurement', 'canine', 'feline'],
            'metadata': {'experimental': True, 'human_in_the_loop': True, 'measurement': 'vhs'},
        },
    },
    {
        'key': 'vet-imgqc-v1',
        'defaults': {
            'name': 'Radiograph Image Quality & Positioning',
            'description': (
                'Workflow aid that scores radiograph technical quality '
                '(exposure, positioning, collimation, motion) at the point of '
                'capture, helping reduce retakes. Does not interpret pathology.'
            ),
            'version': '0.1.0-experimental',
            'connector_class': 'ai_analysis.connectors.chexnet.CheXNetConnector',
            'model_type': 'classification',
            'supported_modalities': ['CR', 'DX'],
            'supported_species': [],  # species-agnostic workflow tool
            'medical_domains': ['radiology', 'workflow'],
            'anatomical_regions': [],
            'is_active': True,
            'use_orchestrator': False,
            'requires_anonymization': False,
            'organization': 'VetImage (experimental)',
            'performance_metrics': {'status': 'pending validation'},
            'validation_dataset': 'Not yet externally validated',
            'training_dataset': 'Internal mixed-species radiographs (placeholder)',
            'limitations': (
                'EXPERIMENTAL workflow tool — quality scoring only, no diagnostic '
                'interpretation. Not a medical device.'
            ),
            'use_cases': ['Retake reduction', 'Positioning feedback for technicians'],
            'tags': ['veterinary', 'image-quality', 'workflow', 'positioning'],
            'metadata': {'experimental': True, 'workflow_only': True},
        },
    },
    {
        'key': 'vet-hip-v1',
        'defaults': {
            'name': 'Canine/Equine Hip Dysplasia Scoring',
            'description': (
                'Decision-support scoring of hip dysplasia from a ventrodorsal '
                'hip-extended radiograph (OFA / BVA / FCI schemes), with '
                'subluxation index and femoral-head congruence per side. Draft '
                'scores only — a veterinarian must review and approve every result.'
            ),
            'version': '0.1.0-experimental',
            'connector_class': 'ai_analysis.connectors.vet_hip.HipDysplasiaConnector',
            'endpoint_url': 'http://vet-hip-service:8000',
            'model_type': 'classification',
            'supported_modalities': ['CR', 'DX'],
            'supported_species': ['canine', 'equine'],
            'medical_domains': ['radiology', 'orthopedics'],
            'anatomical_regions': ['pelvis', 'hip', 'femur'],
            'is_active': True,
            'use_orchestrator': False,
            'requires_anonymization': False,
            'organization': 'VetImage (experimental)',
            'performance_metrics': {'status': 'pending external validation'},
            'validation_dataset': 'Not yet externally validated',
            'training_dataset': 'Internal canine/equine pelvic radiographs (placeholder)',
            'limitations': (
                'EXPERIMENTAL. Not externally validated; no published sensitivity/'
                'specificity. Hip scoring is scheme-dependent and observer-variable. '
                'Use only as a fallible second reader under veterinarian supervision. '
                'Not a medical device; not FDA-cleared.'
            ),
            'use_cases': [
                'Breeding-soundness screening support',
                'Second-reader support for hip-extended views',
            ],
            'tags': ['veterinary', 'orthopedic', 'hip', 'canine', 'equine', 'experimental'],
            'metadata': {'experimental': True, 'human_in_the_loop': True},
        },
    },
    {
        'key': 'vet-dental-v1',
        'defaults': {
            'name': 'Canine/Feline Dental Radiograph Analysis',
            'description': (
                'Decision-support detection of common dental radiographic findings '
                '(tooth resorption, periapical lesions, crown fractures, retained '
                'roots, bone loss) on intraoral radiographs, reported per tooth '
                '(modified Triadan). Draft findings only — clinician confirms.'
            ),
            'version': '0.1.0-experimental',
            'connector_class': 'ai_analysis.connectors.vet_dental.VetDentalConnector',
            'endpoint_url': 'http://vet-dental-service:8000',
            'model_type': 'detection',
            'supported_modalities': ['IO', 'CR', 'DX'],
            'supported_species': ['canine', 'feline'],
            'medical_domains': ['radiology', 'dentistry'],
            'anatomical_regions': ['oral cavity', 'teeth', 'mandible', 'maxilla'],
            'is_active': True,
            'use_orchestrator': False,
            'requires_anonymization': False,
            'organization': 'VetImage (experimental)',
            'performance_metrics': {'status': 'pending external validation'},
            'validation_dataset': 'Not yet externally validated',
            'training_dataset': 'Internal canine/feline intraoral radiographs (placeholder)',
            'limitations': (
                'EXPERIMENTAL. Not externally validated; no published sensitivity/'
                'specificity. Per-tooth findings must be confirmed against the '
                'clinical oral exam. Use only as a fallible second reader under '
                'veterinarian supervision. Not a medical device; not FDA-cleared.'
            ),
            'use_cases': [
                'Flagging suspected tooth resorption / periapical lesions',
                'Second-reader support during dental charting',
            ],
            'tags': ['veterinary', 'dental', 'canine', 'feline', 'experimental'],
            'metadata': {'experimental': True, 'human_in_the_loop': True},
        },
    },
]


class Command(BaseCommand):
    help = 'Seed veterinary AI model catalog entries and hide human-only models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-human', action='store_true',
            help='Do not deactivate the inherited human-only models',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Seeding veterinary AI models…'))

        if not options['keep_human']:
            hidden = AIModel.objects.filter(key__in=HUMAN_MODEL_KEYS, is_active=True).update(is_active=False)
            self.stdout.write(self.style.WARNING(f'  Deactivated {hidden} human-only model(s).'))

        created_n = updated_n = 0
        for spec in VET_MODELS:
            obj, created = AIModel.objects.update_or_create(
                key=spec['key'], defaults=spec['defaults'],
            )
            if created:
                created_n += 1
                self.stdout.write(self.style.SUCCESS(f'  + {obj.key} — {obj.name}'))
            else:
                updated_n += 1
                self.stdout.write(f'  ~ {obj.key} — {obj.name} (updated)')

        self.stdout.write(self.style.SUCCESS(
            f'Done. {created_n} created, {updated_n} updated.'
        ))
