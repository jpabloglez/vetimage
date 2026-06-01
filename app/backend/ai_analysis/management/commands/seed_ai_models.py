"""
Management command to seed initial AI models

Usage:
    python manage.py seed_ai_models

This creates the MIRAGE model entry and can be extended for other models.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from ai_analysis.models import AIModel


class Command(BaseCommand):
    help = 'Seed initial AI model configurations'

    def handle(self, *args, **options):
        """Create initial AI model entries"""

        self.stdout.write(self.style.NOTICE('Seeding AI models...'))

        # Create MIRAGE model
        mirage, created = AIModel.objects.get_or_create(
            key='mirage-v1',
            defaults={
                # Core Identity
                'name': 'MIRAGE',
                'version': '1.0',
                'description': 'MIRAGE is a multimodal foundation model for comprehensive retinal OCT/SLO image analysis. '
                              'It is trained on a large-scale dataset of multimodal data, and is designed to perform a wide '
                              'range of tasks, including disease staging, diagnosis, and layer and lesion segmentation. '
                              'MIRAGE is based on the MultiMAE architecture with Vision Transformer (ViT) backbone, and is '
                              'pretrained using a multi-task learning strategy. The model is available in two sizes: '
                              'MIRAGE-Base and MIRAGE-Large.',

                # Technical Configuration
                'endpoint_url': 'http://mirage-service:8000',
                'connector_class': 'ai_analysis.connectors.mirage.MirageConnector',
                'model_type': 'segmentation',
                'supported_modalities': ['OCT', 'SLO'],  # Optical Coherence Tomography, Scanning Laser Ophthalmoscopy
                'required_parameters': {
                    'modality': {
                        'type': 'string',
                        'description': 'Imaging modality',
                        'options': ['oct', 'slo', 'multimodal']
                    },
                    'task': {
                        'type': 'string',
                        'description': 'Analysis task',
                        'options': ['segmentation', 'classification', 'staging']
                    }
                },
                'default_parameters': {
                    'modality': 'oct',
                    'task': 'segmentation',
                    'model_size': 'base'
                },
                'timeout_seconds': 1800,  # 30 minutes
                'max_retries': 3,
                'retry_delay_seconds': 60,
                'is_active': True,
                'use_orchestrator': False,  # MIRAGE uses REST/Celery dispatch

                # Authors & Attribution
                'authors': [
                    {
                        'name': 'José Morano',
                        'affiliation': 'Medical University of Vienna',
                        'email': ''
                    },
                    {
                        'name': 'Hrvoje Bogunović',
                        'affiliation': 'Medical University of Vienna',
                        'email': ''
                    },
                    {
                        'name': 'Botond Fazekas',
                        'affiliation': 'Medical University of Vienna',
                        'email': ''
                    },
                    {
                        'name': 'Emese Sükei',
                        'affiliation': 'Medical University of Vienna',
                        'email': ''
                    },
                    {
                        'name': 'Ronald Fecso',
                        'affiliation': 'Medical University of Vienna',
                        'email': ''
                    }
                ],
                'organization': 'CD-AIR Lab (Christian Doppler Laboratory for AI in Retina), Medical University of Vienna',

                # Publications & References
                'publication_title': 'Multimodal foundation model and benchmark for comprehensive retinal OCT image analysis',
                'publication_journal': 'npj Digital Medicine',
                'publication_year': 2025,
                'publication_doi': '10.1038/s41746-025-01852-3',
                'publication_url': 'https://doi.org/10.1038/s41746-025-01852-3',
                'citation': 'Morano, J., Fazekas, B., Sükei, E., Fecso, R., Emre, T., Gumpinger, M., '
                           'Faustmann, G., Oghbaie, M., Schmidt-Erfurth, U., & Bogunović, H. (2025). '
                           'Multimodal foundation model and benchmark for comprehensive retinal OCT image analysis. '
                           'npj Digital Medicine, 8(1), 576. https://doi.org/10.1038/s41746-025-01852-3',

                # Code & Resources
                'github_url': 'https://github.com/j-morano/MIRAGE',
                'paper_url': 'https://arxiv.org/abs/2506.08900',
                'demo_url': '',
                'model_card_url': 'https://huggingface.co/j-morano/MIRAGE-Base',

                # Licensing
                'license_name': 'CC BY 4.0',
                'license_url': 'https://creativecommons.org/licenses/by/4.0/',

                # Model Characteristics
                'tags': [
                    'retinal-oct',
                    'ophthalmology',
                    'multimodal',
                    'vision-transformer',
                    'foundation-model',
                    'segmentation',
                    'classification',
                    'pytorch'
                ],
                'medical_domains': ['ophthalmology', 'retinal-diseases'],
                'anatomical_regions': ['retina', 'eye'],

                # Performance Metrics
                'performance_metrics': {
                    'benchmark_tasks': 19,
                    'datasets_evaluated': 16,
                    'model_sizes': 2,
                    'note': 'Significantly outperforms state-of-the-art foundation models across all task types'
                },
                'validation_dataset': '14 publicly available datasets + 2 private datasets (19 tasks total)',
                'training_dataset': 'Large-scale multimodal retinal imaging dataset (OCT/SLO with layer labels)',

                # Use Cases & Examples
                'use_cases': [
                    'Retinal layer segmentation in OCT images',
                    'Lesion detection and segmentation in retinal scans',
                    'Disease staging for retinal conditions (AMD, diabetic retinopathy, etc.)',
                    'Automated diagnosis support for ophthalmologists',
                    'Multi-modal retinal image analysis (OCT + SLO fusion)',
                    'Clinical research and longitudinal studies of retinal diseases'
                ],
                'limitations': 'MIRAGE is specifically designed for retinal OCT and SLO imaging and may have limitations:\n'
                              '- Optimized for retinal imaging only, not applicable to other anatomical regions\n'
                              '- Performance depends on image quality (motion artifacts, poor acquisition can affect results)\n'
                              '- Trained primarily on adult retinal images\n'
                              '- May require fine-tuning for specific rare conditions not well-represented in training data\n'
                              '- Computational requirements: requires GPU for optimal inference speed',
                'example_images': [],

                # Community & Support
                'documentation_url': 'https://github.com/j-morano/MIRAGE#readme',
                'support_url': 'https://github.com/j-morano/MIRAGE/issues',
                'homepage_url': 'https://github.com/j-morano/MIRAGE',

                # Statistics
                'download_count': 0,
                'rating': None,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created AI model: {mirage.name} ({mirage.key})')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ AI model already exists: {mirage.name} ({mirage.key})')
            )

        # Create PICAI model
        picai, created = AIModel.objects.get_or_create(
            key='picai-v1',
            defaults={
                # Core Identity
                'name': 'PI-CAI nnU-Net Baseline',
                'version': '1.0',
                'description': 'Deep learning model for detecting clinically significant prostate cancer (csPCa) from '
                              'biparametric MRI. Uses nnU-Net 5-fold ensemble trained on 1295 prostate bpMRI scans. '
                              'The model generates a detection map showing likelihood of cancer at each voxel, plus a '
                              'case-level confidence score. Developed for the PI-CAI (Prostate Imaging: Cancer AI) challenge.',

                # Technical Configuration
                'endpoint_url': 'picai-service:50051',  # Orchestrator gRPC endpoint
                'connector_class': 'ai_analysis.connectors.picai.PICAIConnector',
                'model_type': 'segmentation',
                'supported_modalities': ['T2W', 'ADC', 'HBV'],  # T2-weighted, ADC map, High b-value DWI
                'required_parameters': {
                    'adc_image_id': {
                        'type': 'integer',
                        'description': 'ID of the ADC (Apparent Diffusion Coefficient) MRI image - REQUIRED for segmentation',
                        'required': True
                    }
                },
                # Note: T2W image is passed as the primary input_image_id
                # For segmentation: T2W (input_image_id) + ADC (adc_image_id) are REQUIRED
                # HBV (hbv_image_id) is optional and improves performance
                'default_parameters': {
                    'output_format': 'mha',
                    'ensemble_folds': 5
                },
                'timeout_seconds': 600,  # 10 minutes for nnU-Net inference
                'max_retries': 2,
                'retry_delay_seconds': 30,
                'is_active': True,
                'use_orchestrator': True,  # PICAI uses gRPC via Orchestrator

                # Authors & Attribution
                'authors': [
                    {
                        'name': 'Joeran Bosma',
                        'affiliation': 'Diagnostic Image Analysis Group, Radboud UMC',
                        'email': 'Joeran.Bosma@radboudumc.nl'
                    },
                    {
                        'name': 'Anindo Saha',
                        'affiliation': 'Diagnostic Image Analysis Group, Radboud UMC',
                        'email': 'Anindya.Shaha@radboudumc.nl'
                    },
                    {
                        'name': 'Henkjan Huisman',
                        'affiliation': 'Diagnostic Image Analysis Group, Radboud UMC',
                        'email': 'Henkjan.Huisman@radboudumc.nl'
                    }
                ],
                'organization': 'Diagnostic Image Analysis Group, Radboud University Medical Center, Nijmegen, Netherlands',

                # Publications & References
                'publication_title': 'PI-CAI: Prostate Imaging - Cancer AI Challenge',
                'publication_journal': 'Grand Challenge',
                'publication_year': 2023,
                'publication_doi': '10.5281/zenodo.6624726',
                'publication_url': 'https://grand-challenge.org/algorithms/pi-cai-nnu-net-baseline/',
                'citation': 'Bosma, J. S., Saha, A., Hosseinzadeh, M., Slootweg, I., de Rooij, M., & Huisman, H. J. (2023). '
                           'PI-CAI: Public Training and Development Dataset for Prostate Imaging. '
                           'Zenodo. https://doi.org/10.5281/zenodo.6624726',

                # Code & Resources
                'github_url': 'https://github.com/DIAGNijmegen/picai_baseline',
                'paper_url': 'https://doi.org/10.5281/zenodo.6624726',
                'demo_url': '',
                'model_card_url': '',

                # Licensing
                'license_name': 'Apache 2.0',
                'license_url': 'https://github.com/DIAGNijmegen/picai_baseline/blob/main/LICENSE',

                # Model Characteristics
                'tags': [
                    'prostate',
                    'mri',
                    'cancer-detection',
                    'nnunet',
                    'segmentation',
                    'urology',
                    'radiology',
                    'bpmri',
                    'deep-learning'
                ],
                'medical_domains': ['urology', 'radiology', 'oncology'],
                'anatomical_regions': ['prostate', 'pelvis'],

                # Performance Metrics
                'performance_metrics': {
                    'AUROC': 0.85,
                    'Sensitivity': 0.90,
                    'Specificity': 0.75,
                    'Dice Score': 0.72,
                    'note': 'Performance metrics from PI-CAI challenge validation set'
                },
                'validation_dataset': 'PI-CAI Development Dataset (300 cases)',
                'training_dataset': 'PI-CAI Public Training Dataset (1295 biparametric MRI scans with histopathology-confirmed labels)',

                # Use Cases & Examples
                'use_cases': [
                    'Detection of clinically significant prostate cancer (ISUP ≥ 2)',
                    'Risk stratification for prostate cancer from MRI',
                    'Computer-aided diagnosis support for radiologists',
                    'Triage tool for biopsy decision-making',
                    'Lesion localization in biparametric MRI'
                ],
                'limitations': 'IMPORTANT - Research use only:\n'
                              '- Requires validation in clinical setting before deployment\n'
                              '- Trained exclusively on Siemens Healthineers (Skyra/Prisma/Trio/Avanto) and Philips Medical Systems (Ingenia/Achieva) scanners\n'
                              '- Not compatible with endorectal coils\n'
                              '- Requires well-aligned T2W, ADC, and HBV sequences\n'
                              '- Target population: Patients with raised PSA or clinical suspicion, without prior treatment\n'
                              '- Prostate must be localized within 460 cm³ from center coordinate\n'
                              '- Not validated for post-treatment, prior positive biopsy, or images with artifacts',
                'example_images': [],

                # Community & Support
                'documentation_url': 'https://github.com/DIAGNijmegen/picai_baseline/blob/main/nnunet_baseline.md',
                'support_url': 'https://github.com/DIAGNijmegen/picai_baseline/issues',
                'homepage_url': 'https://grand-challenge.org/algorithms/pi-cai-nnu-net-baseline/',

                # Statistics
                'download_count': 0,
                'rating': None,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created AI model: {picai.name} ({picai.key})')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ AI model already exists: {picai.name} ({picai.key})')
            )

        # Create CheXNet model
        chexnet, created = AIModel.objects.get_or_create(
            key='chexnet-v1',
            defaults={
                # Core Identity
                'name': 'CheXNet',
                'version': '1.0',
                'description': 'CheXNet is a 121-layer DenseNet trained on over 100,000 frontal chest X-ray images '
                              'from the ChestX-ray14 dataset. It classifies 14 thoracic pathologies including pneumonia, '
                              'atelectasis, cardiomegaly, effusion, and pneumothorax. The model achieves radiologist-level '
                              'performance on pneumonia detection and provides class activation maps for interpretability.',

                # Technical Configuration
                'endpoint_url': 'http://chexnet-service:8000',
                'connector_class': 'ai_analysis.connectors.chexnet.CheXNetConnector',
                'model_type': 'classification',
                'supported_modalities': ['CR', 'DX'],  # Computed Radiography, Digital X-ray
                'required_parameters': {},
                'default_parameters': {
                    'threshold': 0.5,
                    'return_heatmap': False,
                },
                'timeout_seconds': 120,  # 2 minutes for classification
                'max_retries': 3,
                'retry_delay_seconds': 15,
                'is_active': True,
                'use_orchestrator': False,  # CheXNet uses REST/Celery dispatch

                # Authors & Attribution
                'authors': [
                    {
                        'name': 'Pranav Rajpurkar',
                        'affiliation': 'Stanford University',
                        'email': ''
                    },
                    {
                        'name': 'Jeremy Irvin',
                        'affiliation': 'Stanford University',
                        'email': ''
                    },
                    {
                        'name': 'Andrew Y. Ng',
                        'affiliation': 'Stanford University',
                        'email': ''
                    }
                ],
                'organization': 'Stanford ML Group, Stanford University',

                # Publications & References
                'publication_title': 'CheXNet: Radiologist-Level Pneumonia Detection on Chest X-Rays with Deep Learning',
                'publication_journal': 'arXiv preprint',
                'publication_year': 2017,
                'publication_doi': '10.48550/arXiv.1711.05225',
                'publication_url': 'https://arxiv.org/abs/1711.05225',
                'citation': 'Rajpurkar, P., Irvin, J., Zhu, K., Yang, B., Mehta, H., Duan, T., Ding, D., Bagul, A., '
                           'Langlotz, C., Shpanskaya, K., Lungren, M. P., & Ng, A. Y. (2017). '
                           'CheXNet: Radiologist-Level Pneumonia Detection on Chest X-Rays with Deep Learning. '
                           'arXiv preprint arXiv:1711.05225.',

                # Code & Resources
                'github_url': 'https://github.com/arnoweng/CheXNet',
                'paper_url': 'https://arxiv.org/abs/1711.05225',
                'demo_url': '',
                'model_card_url': '',

                # Licensing
                'license_name': 'MIT',
                'license_url': 'https://github.com/arnoweng/CheXNet/blob/master/LICENSE',

                # Model Characteristics
                'tags': [
                    'chest-xray',
                    'classification',
                    'densenet',
                    'pneumonia',
                    'radiology',
                    'deep-learning',
                    'pytorch',
                    'heatmap',
                ],
                'medical_domains': ['radiology', 'pulmonology', 'emergency-medicine'],
                'anatomical_regions': ['chest', 'lung', 'thorax'],

                # Performance Metrics
                'performance_metrics': {
                    'AUROC_Pneumonia': 0.7680,
                    'AUROC_Average': 0.8414,
                    'note': 'Exceeds average radiologist F1 on pneumonia detection. '
                           'Average AUROC across all 14 pathologies.',
                },
                'validation_dataset': 'ChestX-ray14 test set (25,596 images)',
                'training_dataset': 'ChestX-ray14 (112,120 frontal chest X-ray images from 30,805 unique patients)',

                # Use Cases & Examples
                'use_cases': [
                    'Automated screening of chest X-rays for common pathologies',
                    'Pneumonia detection and triage',
                    'Identification of pleural effusion and pneumothorax',
                    'Cardiomegaly screening',
                    'Radiologist decision support for chest X-ray interpretation',
                ],
                'limitations': 'Research use only - important limitations:\n'
                              '- Trained on frontal chest X-rays only (PA and AP views)\n'
                              '- Not validated for lateral views\n'
                              '- Performance may vary across different X-ray equipment manufacturers\n'
                              '- Labels derived from NLP-extracted reports (may contain noise)\n'
                              '- Does not detect conditions outside the 14 trained pathologies\n'
                              '- Heatmaps are for visualization only, not pixel-level segmentation',
                'example_images': [],

                # Community & Support
                'documentation_url': 'https://github.com/arnoweng/CheXNet#readme',
                'support_url': 'https://github.com/arnoweng/CheXNet/issues',
                'homepage_url': 'https://stanfordmlgroup.github.io/projects/chexnet/',

                # Statistics
                'download_count': 0,
                'rating': None,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created AI model: {chexnet.name} ({chexnet.key})')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ AI model already exists: {chexnet.name} ({chexnet.key})')
            )

        # Create FastSurfer model
        fastsurfer, created = AIModel.objects.get_or_create(
            key='fastsurfer-v2',
            defaults={
                # Core Identity
                'name': 'FastSurfer v2',
                'version': '2.0',
                'description': 'FastSurfer is a fast, deep-learning based neuroimaging pipeline for whole-brain '
                              'MRI segmentation and cortical parcellation. It produces FreeSurfer-compatible outputs '
                              'in ~90 seconds on GPU (vs. ~6 hours for FreeSurfer). The seg-only pipeline runs without '
                              'a FreeSurfer license and generates volumetric segmentations of 95+ brain structures. '
                              'Developed by the Deep-MI Lab at DZNE (German Center for Neurodegenerative Diseases).',

                # Technical Configuration
                'endpoint_url': 'fastsurfer-service:50051',  # Orchestrator gRPC endpoint
                'connector_class': 'ai_analysis.connectors.fastsurfer.FastSurferConnector',
                'model_type': 'segmentation',
                'supported_modalities': ['MR'],  # T1-weighted structural MRI
                'required_parameters': {},
                'default_parameters': {
                    'device': 'cuda',
                    'threads': 4,
                    'use_3T': True,
                },
                'timeout_seconds': 300,  # 5 minutes on GPU
                'max_retries': 2,
                'retry_delay_seconds': 30,
                'is_active': True,
                'use_orchestrator': True,  # FastSurfer uses gRPC via Orchestrator

                # Authors & Attribution
                'authors': [
                    {
                        'name': 'Leonie Henschel',
                        'affiliation': 'German Center for Neurodegenerative Diseases (DZNE), Bonn',
                        'email': ''
                    },
                    {
                        'name': 'David Kügler',
                        'affiliation': 'German Center for Neurodegenerative Diseases (DZNE), Bonn',
                        'email': ''
                    },
                    {
                        'name': 'Martin Reuter',
                        'affiliation': 'German Center for Neurodegenerative Diseases (DZNE), Bonn / '
                                       'Harvard Medical School / Massachusetts General Hospital',
                        'email': ''
                    },
                ],
                'organization': 'Deep-MI Lab, German Center for Neurodegenerative Diseases (DZNE), Bonn, Germany',

                # Publications & References
                'publication_title': 'FastSurfer - A fast and accurate deep learning based neuroimaging pipeline',
                'publication_journal': 'NeuroImage',
                'publication_year': 2020,
                'publication_doi': '10.1016/j.neuroimage.2020.117012',
                'publication_url': 'https://doi.org/10.1016/j.neuroimage.2020.117012',
                'citation': 'Henschel, L., Conjeti, S., Estrada, S., Diers, K., Fischl, B., & Reuter, M. (2020). '
                           'FastSurfer - A fast and accurate deep learning based neuroimaging pipeline. '
                           'NeuroImage, 219, 117012. https://doi.org/10.1016/j.neuroimage.2020.117012',

                # Code & Resources
                'github_url': 'https://github.com/Deep-MI/FastSurfer',
                'paper_url': 'https://doi.org/10.1016/j.neuroimage.2020.117012',
                'demo_url': '',
                'model_card_url': 'https://hub.docker.com/r/deepmi/fastsurfer',

                # Licensing
                'license_name': 'Apache 2.0',
                'license_url': 'https://github.com/Deep-MI/FastSurfer/blob/stable/LICENSE',

                # Model Characteristics
                'tags': [
                    'brain-mri',
                    'neuroimaging',
                    'segmentation',
                    'parcellation',
                    'whole-brain',
                    't1w',
                    'freesurfer-compatible',
                    'deep-learning',
                    'pytorch',
                ],
                'medical_domains': ['neurology', 'neuroimaging'],
                'anatomical_regions': ['brain'],

                # Performance Metrics
                'performance_metrics': {
                    'Dice_vs_FreeSurfer': 0.95,
                    'runtime_GPU': '~90 seconds',
                    'runtime_CPU': '~20-30 minutes',
                    'segmented_structures': 95,
                    'note': 'DICE ≈ 0.95 vs FreeSurfer ground truth across 95 brain structures. '
                           'Evaluated on HCP, ADNI, and OASIS datasets.'
                },
                'validation_dataset': 'HCP, ADNI, OASIS datasets (multi-site, multi-scanner)',
                'training_dataset': 'Large-scale multi-site T1w MRI with FreeSurfer-derived labels',

                # Use Cases & Examples
                'use_cases': [
                    'Whole-brain MRI segmentation (95+ structures)',
                    'Brain volume analysis and morphometry',
                    'Cortical parcellation (DKT atlas)',
                    'Longitudinal brain change monitoring',
                    'Neurodegeneration studies (Alzheimer\'s, Parkinson\'s)',
                    'Pre-operative planning and neurosurgical guidance',
                    'Quality control of T1w MRI acquisitions',
                ],
                'limitations': 'FastSurfer seg-only pipeline limitations:\n'
                              '- T1-weighted MRI only (not CT, T2, fMRI, or DWI)\n'
                              '- Optimised for 1 mm isotropic resolution (≤ 1.5 mm slice thickness recommended)\n'
                              '- GPU strongly recommended; CPU mode is functional but slow (~20-30 min)\n'
                              '- 3T scanner assumed by default (--3T flag); adjust for 1.5T acquisitions\n'
                              '- Seg-only mode: no surface reconstruction (no cortical thickness, no pial surfaces)\n'
                              '- Not validated for paediatric populations or severe pathology/resection cases\n'
                              '- Research use only — not a CE/FDA-cleared medical device',
                'example_images': [],

                # Community & Support
                'documentation_url': 'https://github.com/Deep-MI/FastSurfer#readme',
                'support_url': 'https://github.com/Deep-MI/FastSurfer/issues',
                'homepage_url': 'https://deep-mi.org/research/fastsurfer/',

                # Statistics
                'download_count': 0,
                'rating': None,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created AI model: {fastsurfer.name} ({fastsurfer.key})')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ AI model already exists: {fastsurfer.name} ({fastsurfer.key})')
            )

        # ----------------------------------------------------------------
        # STU-Net-S  (Scalable U-Net Small — TotalSegmentator 104-organ)
        # ----------------------------------------------------------------
        _stunet_common = dict(
            connector_class='ai_analysis.connectors.nnunet.NNUNetConnector',
            endpoint_url='',        # local subprocess — no network endpoint
            model_type='segmentation',
            supported_modalities=['CT'],
            timeout_seconds=3600,
            is_active=True,
            use_orchestrator=False,
            authors=[{
                'name': 'Ziyan Huang',
                'affiliation': 'Shanghai AI Laboratory',
            }],
            organization='OpenMEDLab / Shanghai AI Laboratory',
            publication_title='STU-Net: Scalable and Transferable Medical Image Segmentation Models Empowered by Large-Scale Supervised Pre-training',
            publication_journal='arXiv',
            publication_year=2023,
            github_url='https://github.com/openmedlab/STU-Net',
            paper_url='https://arxiv.org/abs/2304.06716',
            license_name='Apache-2.0',
            tags=['nnunet', 'segmentation', 'multi-organ', 'ct', 'totalsegmentator'],
            medical_domains=['radiology', 'oncology'],
            anatomical_regions=[
                'liver', 'spleen', 'pancreas', 'kidney', 'gallbladder',
                'esophagus', 'stomach', 'aorta', 'lung',
            ],
            required_parameters={},
            default_parameters={},
        )

        _stunet_label_map = {
            '1':  'spleen',        '2':  'right_kidney',   '3':  'left_kidney',
            '4':  'gallbladder',   '5':  'esophagus',      '6':  'liver',
            '7':  'stomach',       '8':  'aorta',          '9':  'inferior_vena_cava',
            '10': 'portal_vein',   '11': 'pancreas',       '12': 'right_adrenal',
            '13': 'left_adrenal',  '14': 'duodenum',
        }

        stunet_s, created = AIModel.objects.get_or_create(
            key='stunet-s-v1',
            defaults={
                **_stunet_common,
                'name': 'STU-Net-S',
                'version': '1.0',
                'description': (
                    'STU-Net Small: scalable nnU-Net variant trained on TotalSegmentator v1 '
                    'for 104-class CT whole-body segmentation. Smallest variant (14.6M params) '
                    'with strong performance on abdominal organs. Uses nnU-Net v2 framework.'
                ),
                'metadata': {
                    'nnunet_dataset_id': 'Dataset291_TotalSegmentator_v2_small_part1',
                    'nnunet_config':     '3d_fullres',
                    'nnunet_folds':      'all',
                    'model_size':        'small',
                    'num_params':        '14.6M',
                },
                'label_map': _stunet_label_map,
                'performance_metrics': {'DSC_mean': 0.814},
                'validation_dataset': 'TotalSegmentator v1',
                'training_dataset': 'TotalSegmentator v1 (1204 CT scans)',
            },
        )
        self._log_model(stunet_s, created)

        stunet_b, created = AIModel.objects.get_or_create(
            key='stunet-b-v1',
            defaults={
                **_stunet_common,
                'name': 'STU-Net-B',
                'version': '1.0',
                'description': (
                    'STU-Net Base: balanced accuracy/speed nnU-Net variant trained on '
                    'TotalSegmentator v1. 58.3M parameters. Recommended for clinical workstations.'
                ),
                'metadata': {
                    'nnunet_dataset_id': 'Dataset291_TotalSegmentator_v2_small_part1',
                    'nnunet_config':     '3d_fullres',
                    'nnunet_folds':      'all',
                    'model_size':        'base',
                    'num_params':        '58.3M',
                },
                'label_map': _stunet_label_map,
                'performance_metrics': {'DSC_mean': 0.836},
                'validation_dataset': 'TotalSegmentator v1',
                'training_dataset': 'TotalSegmentator v1 (1204 CT scans)',
            },
        )
        self._log_model(stunet_b, created)

        stunet_l, created = AIModel.objects.get_or_create(
            key='stunet-l-v1',
            defaults={
                **_stunet_common,
                'name': 'STU-Net-L',
                'version': '1.0',
                'description': (
                    'STU-Net Large: high-accuracy nnU-Net variant (440M params) for '
                    'TotalSegmentator whole-body CT segmentation. Best accuracy in the STU-Net family.'
                ),
                'metadata': {
                    'nnunet_dataset_id': 'Dataset291_TotalSegmentator_v2_small_part1',
                    'nnunet_config':     '3d_fullres',
                    'nnunet_folds':      'all',
                    'model_size':        'large',
                    'num_params':        '440M',
                },
                'label_map': _stunet_label_map,
                'performance_metrics': {'DSC_mean': 0.850},
                'validation_dataset': 'TotalSegmentator v1',
                'training_dataset': 'TotalSegmentator v1 (1204 CT scans)',
            },
        )
        self._log_model(stunet_l, created)

        # ----------------------------------------------------------------
        # MIS-FM  (Medical Image Segmentation Foundation Model)
        # ----------------------------------------------------------------
        misfm, created = AIModel.objects.get_or_create(
            key='misfm-v1',
            defaults={
                'name': 'MIS-FM',
                'version': '1.0',
                'description': (
                    'MIS-FM: universal foundation model for medical image segmentation '
                    'trained on 14,012 CT/MRI volumes across 12 datasets. Supports 8 '
                    'cross-dataset shared organ targets (A-Eval benchmark). Uses nnU-Net v2 '
                    'as the segmentation backbone with pre-trained MedMAE encoder.'
                ),
                'connector_class': 'ai_analysis.connectors.nnunet.NNUNetConnector',
                'endpoint_url': '',
                'model_type': 'segmentation',
                'supported_modalities': ['CT', 'MRI'],
                'timeout_seconds': 3600,
                'is_active': True,
                'use_orchestrator': False,
                'authors': [{'name': 'Jiahao Li', 'affiliation': 'Shanghai AI Laboratory'}],
                'organization': 'OpenMEDLab / Shanghai AI Laboratory',
                'publication_title': 'MIS-FM: 3D Medical Image Segmentation using Foundation Models Pretrained on a Large-Scale Unannotated Dataset',
                'publication_journal': 'arXiv',
                'publication_year': 2023,
                'github_url': 'https://github.com/openmedlab/MIS-FM',
                'paper_url': 'https://arxiv.org/abs/2306.16925',
                'license_name': 'Apache-2.0',
                'tags': ['nnunet', 'foundation-model', 'multi-organ', 'ct', 'mri', 'a-eval'],
                'medical_domains': ['radiology', 'oncology'],
                'anatomical_regions': [
                    'liver', 'right_kidney', 'left_kidney', 'spleen',
                    'pancreas', 'gallbladder', 'esophagus', 'stomach',
                ],
                'required_parameters': {},
                'default_parameters': {},
                'metadata': {
                    'nnunet_dataset_id': 'Dataset101_MISFM',
                    'nnunet_config':     '3d_fullres',
                    'nnunet_folds':      'all',
                },
                'label_map': {
                    '1': 'liver',        '2': 'right_kidney', '3': 'left_kidney',
                    '4': 'spleen',       '5': 'pancreas',     '6': 'gallbladder',
                    '7': 'esophagus',    '8': 'stomach',
                },
                'performance_metrics': {
                    'DSC_liver': 0.956, 'DSC_spleen': 0.947,
                    'DSC_kidney_R': 0.941, 'DSC_kidney_L': 0.940,
                    'DSC_pancreas': 0.782,
                },
                'validation_dataset': 'A-Eval benchmark (8-organ CT)',
                'training_dataset': '14,012 CT/MRI volumes (12 public datasets)',
            },
        )
        self._log_model(misfm, created)

        # Always enforce correct orchestrator routing flags (handles pre-existing records)
        AIModel.objects.filter(key__in=['mirage-v1', 'chexnet-v1']).update(use_orchestrator=False)
        AIModel.objects.filter(key__in=['picai-v1', 'fastsurfer-v2']).update(use_orchestrator=True)
        AIModel.objects.filter(
            key__in=['stunet-s-v1', 'stunet-b-v1', 'stunet-l-v1', 'misfm-v1']
        ).update(use_orchestrator=False)
        self.stdout.write(self.style.SUCCESS('✓ Orchestrator routing flags enforced'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('AI model seeding complete!'))
        self.stdout.write(self.style.NOTICE(f'Total models: {AIModel.objects.count()}'))

    def _log_model(self, model_obj, created: bool):
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created AI model: {model_obj.name} ({model_obj.key})'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ AI model already exists: {model_obj.name} ({model_obj.key})'))
