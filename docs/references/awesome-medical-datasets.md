# Awesome Medical Dataset — Reference Index

> Source: https://github.com/openmedlab/Awesome-Medical-Dataset
> Stars: 1,724 | Gathered: 2026-03-18
> Purpose: Datasets relevant for testing/benchmarking the OpenMedLab platform

---

## Overview

Curated collection of medical imaging and clinical datasets, organized by body region and modality.
All clinical datasets in this list underwent DICOM de-identification before public release —
confirming that anonymization is a prerequisite for any data sharing pipeline.

---

## Datasets by Category

### Whole Body / Multi-Organ (CT)

| Dataset | Modality | Task | Classes | Notes |
|---|---|---|---|---|
| **TotalSegmentator** | CT | Segmentation | 104 organs | Most comprehensive, used to train STU-Net |
| **FLARE22** | CT | Segmentation | 13 organs | MICCAI 2022 challenge |
| **AMOS** | CT + MRI | Segmentation | 15 organs | Multi-modality abdominal |
| **WORD** | CT | Segmentation | 16 organs | Whole abdominal organ dataset |
| **BTCV** | CT | Segmentation | 13 organs | Beyond the Cranial Vault |
| **AutoPET** | PET-CT | Detection + Segmentation | Lesions | Whole-body tumor lesion detection |

### Brain / Head

| Dataset | Modality | Task | Notes |
|---|---|---|---|
| **BraTS** | MRI (T1/T2/FLAIR/T1ce) | Segmentation | Brain tumor, annual MICCAI challenge |
| **ATLAS** | MRI | Segmentation | Stroke lesion segmentation |
| **ABIDE** | fMRI | Classification | Autism spectrum disorder |
| **ADNI** | MRI | Classification | Alzheimer's disease (registration required) |

### Chest / Lung

| Dataset | Modality | Task | Notes |
|---|---|---|---|
| **CheXpert** | Chest X-ray | Classification | 14 findings, Stanford; 224K images |
| **MIMIC-CXR** | Chest X-ray + Reports | Report generation | 227K images with radiology reports |
| **Luna16** | CT | Nodule detection | 888 CT scans |
| **NLSt** | CT | Lung cancer screening | |
| **ChestX-ray14** | Chest X-ray | Classification | 14 diseases, 112K images (NIH) |

### Abdomen / GI

| Dataset | Modality | Task | Notes |
|---|---|---|---|
| **Kvasir-SEG** | Endoscopy | Segmentation | Polyp segmentation, 1,000 images |
| **CVC-ClinicDB** | Colonoscopy | Segmentation | 612 images |
| **Synapse** | CT | Multi-organ segmentation | 30 CT scans, 8 organs |

### Pathology / WSI

| Dataset | Modality | Task | Notes |
|---|---|---|---|
| **Camelyon16/17** | WSI (H&E) | Detection | Lymph node metastasis; AUC benchmark |
| **TCGA** | WSI | Classification / Survival | Pan-cancer atlas; requires TCIA access |
| **PANDA** | WSI (H&E) | Grading | Prostate cancer Gleason grading |
| **BACH** | WSI (H&E) | Classification | Breast cancer histology |

### Retina / Ophthalmology

| Dataset | Modality | Task | Notes |
|---|---|---|---|
| **DRIVE** | Fundus | Vessel segmentation | 40 images |
| **STARE** | Fundus | Vessel segmentation | |
| **REFUGE** | Fundus | Glaucoma detection + disc segmentation | |
| **ORIGA** | Fundus | Glaucoma | |

### Ultrasound

| Dataset | Modality | Task | Notes |
|---|---|---|---|
| **TN3K** | Thyroid US | Segmentation | 3,493 images; used in DeblurringMIM |
| **BUSI** | Breast US | Segmentation + Classification | 780 images |
| **US-TNBC** | Breast US | Classification | |
| **EchoNet-Dynamic** | Cardiac Echo | Ejection fraction regression | 10K videos |

---

## Data Access Patterns

Most datasets require:
1. **Registration** on dataset hosting platform (TCIA, PhysioNet, Kaggle, Zenodo)
2. **Data use agreement** (DUA) — especially for clinical datasets
3. **IRB or ethics board documentation** for datasets with patient data

**Platforms hosting DICOM datasets:**
- TCIA (The Cancer Imaging Archive): https://www.cancerimagingarchive.net/
- PhysioNet: https://physionet.org/
- Grand Challenge: https://grand-challenge.org/
- Zenodo: https://zenodo.org/

---

## Relevance to Platform Testing

These datasets can be used to:

1. **End-to-end pipeline testing** — upload DICOM files, run AI inference, verify output
2. **Anonymization validation** — verify PHI removal on known-clean test DICOMs
3. **BIDS conversion testing** — validate dcm2niix output structure on public CT data
4. **AI model benchmarking** — compare platform connector output against published metrics
5. **Segmentation visualization testing** — test DICOM SEG round-trip with labeled masks

**Recommended test dataset for the platform (small, permissive):**
- **Kvasir-SEG**: 1,000 polyp images, MIT license, PNG format (can be converted to DICOM)
- **DRIVE**: 40 fundus images, permissive license
- **TotalSegmentator samples**: 10 anonymized CT scans available on Zenodo under CC-BY 4.0
