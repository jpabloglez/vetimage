# OpenMEDLab AI Models — Technical Reference

> Gathered: 2026-03-18
> Purpose: Technical details for potential integration into OpenMedLab platform

---

## Segmentation Models

### STU-Net
**Repo:** https://github.com/openmedlab/STU-Net
**Stars:** 115 | **License:** CC-BY-NC 4.0

**Architecture:** Scalable convolutional blocks built on nnU-Net. Four sizes:
- Small (S): 14.6M params
- Base (B): 58.26M params
- Large (L): 440M params
- **Huge (H): 1.457B params** (largest publicly released medical segmentation model)

**Pre-training:** TotalSegmentator dataset — 1,204 CT scans, 104 anatomical structures.
**Input:** 128×128×128 voxel crops from CT volumes (NIfTI).
**Inference CLI:**
```bash
nnUNet_predict -i <input_dir> -o <output_dir> -t 101 -m 3d_fullres
```
**Dependencies:** torch==1.10, nnUNet==1.7.0
**Integration pattern:** subprocess wrapper, same as FastSurfer connector.

---

### MIS-FM (3D CT Segmentation Foundation Model)
**Repo:** https://github.com/openmedlab/MIS-FM
**Stars:** 246

**Architecture:** Two variants:
- FMUNet — modified 3D UNet
- PCT-Net — hybrid CNN-Transformer

**Pre-training:** Volume Fusion (VolF) self-supervised on multi-organ abdominal CT.
**Framework:** PyMIC==0.5.0 (config-driven).
**Inference:**
```bash
python net_run.py test demo/config.cfg
```
**Benchmark:** 91.80% Dice on left atrial segmentation.

---

### MedLSAM (Localize and Segment Anything)
**Repo:** https://github.com/openmedlab/MedLSAM
**Stars:** 518

**Pipeline:** MedLAM (localization) → SAM (segmentation)
**Training data:** 14,012 CT scans (self-supervised).
**Input:** NIfTI (.nii.gz). 6 extreme point annotations on template image.
**Output:** NPZ + PNG segmentation masks.
**GPU requirement:** 12GB VRAM minimum.
**Two inference modes:**
- WPL (whole-patch localization)
- SPL (sub-patch for fine granularity)

---

### SAM-Med2D
**Repo:** https://github.com/openmedlab/SAM-Med2D
**Stars:** 76

**Architecture:** SAM (Segment Anything Model) adapted for medical 2D images.
- Frozen image encoder + learnable adapter layers in each Transformer block
- Prompt encoder and mask decoder: fully updated

**Training:** 4.6M images / 19.7M masks, 10 modalities, 31 organs.
**Performance:** 35 FPS at 256×256. Dice: 79.30% (bounding box), 70.01% (1-point prompt).
**Inference flags:** `--image_size 256`, `--point_num 1`, `--boxes_prompt`
**Deployment:** Local Python + Gradio demo. No REST/gRPC API.

---

### SAM-Med3D
**Repo:** https://github.com/openmedlab/SAM-Med3D
**Stars:** 41

**Architecture:** SAM extended to 3D volumetric segmentation.
**Input:** 3D NIfTI volumes.
**Prompt types:** 3D point prompts.
**Use case:** Interactive segmentation of volumetric DICOM-origin data.

---

### Swin-UMamba
**Repo:** https://github.com/openmedlab/Swin-UMamba
**Stars:** 12

**Architecture:** Mamba state-space model UNet + ImageNet pretraining via Swin transformer.
**Domains:** AbdomenMRI, Endoscopy, Microscopy.
**Pipeline:** nnUNetv2 preprocessing.
**Performance:** Outperforms U-Mamba by avg +2.72%. Lower memory than ViT-based approaches.
**Dependencies:** PyTorch 2.0.1.

---

### A-Eval (Cross-dataset Abdominal Segmentation Benchmark)
**Repo:** https://github.com/openmedlab/A-Eval
**Stars:** 4

**Benchmark scope:** 5 public datasets:
- FLARE22, AMOS, WORD, TotalSegmentator, BTCV
- 257 CT + 20 MR images
- 8 shared organ classes

**Metrics:** DSC (Dice Similarity Coefficient) and NSD (Normalized Surface Dice).
**Tools:** `label_systems.py`, `convert_label_2_overlap_label.py`
**Note:** Defines a cross-dataset organ label taxonomy useful for structured report generation.

**8 shared organ classes:**
1. Liver
2. Right Kidney
3. Left Kidney
4. Spleen
5. Pancreas
6. Gallbladder
7. Esophagus
8. Stomach

---

## Specialty Imaging Models

### USFM (Ultrasound Foundation Model)
**Repo:** https://github.com/openmedlab/USFM
**Stars:** 323

**Architecture:** ViT backbone + masked image modeling with **frequency domain masking**.
**Tasks:** Classification, segmentation, image enhancement.
**Framework:** PyTorch Lightning + Hydra config.
**Inference:**
```bash
python main.py experiment=task/[Seg|Cls] data=<dataset> model=<model>
```
**Weights:** `USFM_latest.pth`
**Significance:** First publicly available ultrasound foundation model.

---

### DeblurringMIM (Thyroid Ultrasound)
**Repo:** https://github.com/openmedlab/DeblurringMIM
**Stars:** 131

**Pre-training:** 280K thyroid ultrasound images. Gaussian blur (σ=1.1) pretraining pairs.
**Variants:** Deblurring MAE and Deblurring ConvMAE.
**Tasks:** Classification + semantic segmentation (U-Net++).
**Benchmark:** 74.96% IoU on TN3K thyroid segmentation.

---

### RETFound (Retinal Foundation Model)
**Repo:** https://github.com/openmedlab/RETFound_MAE
**Stars:** 102 | **Published:** Nature 2023

**Architecture:** ViT-Large/patch16 MAE.
**Pre-training:** 1.6M unlabeled retinal images (fundus + OCT).
**Downstream tasks:** Diabetic retinopathy, glaucoma, cataracts, heart failure prediction.
**Inference:**
```bash
python -m torch.distributed.launch ... main_finetune.py
```
**Significance:** Nature-published; high clinical credibility.

---

### Endo-FM (Endoscopy)
**Repo:** https://github.com/openmedlab/Endo-FM
**Stars:** 218

**Architecture:** Video transformer for spatial-temporal analysis.
**Pre-training:** 33K video clips / 5M frames.
**Tasks:** Classification (PolypDiag), segmentation (CVC-12k), detection (KUMC).
**Framework:** PyTorch 1.8.0+.

---

### BrainMVP (Multi-Modal Brain MRI)
**Repo:** https://github.com/openmedlab/BrainMVP
**Stars:** 81

**Architecture:** Two variants — Uniformer and UNet (MONAI-based).
**Pre-training on 2.4M+ images** from 16,022 multi-parametric MRI scans.
**Three proxy tasks:**
1. Cross-modal reconstruction
2. Modality-aware contrastive learning
3. Modality template distillation

**Downstream:** 6 segmentation benchmarks (up to +14.47% Dice), 4 classification tasks.
**Significance:** Directly relevant to the existing FastSurfer brain MRI workflow.

---

## Pathology / WSI Models

### PathoDuet (Histopathology Foundation Model)
**Repo:** https://github.com/openmedlab/PathoDuet
**Stars:** 222

**Architecture:** ViT-B/16. Two pretext tasks:
1. Cross-scale positioning
2. Cross-stain transferring (H&E ↔ IHC)

**Tasks:** Patch classification, WSI classification (CLAM-SB), PD-L1 expression quantification.
**Performance:** WSI classification AUC 0.956 on Camelyon16.
**Input:** H&E and IHC stained histopathology patches.

---

### BROW (Whole Slide Image Analysis)
**Repo:** https://github.com/openmedlab/BROW
**Stars:** 122

**Architecture:** ViT-S/16, ViT-B/16, ViT-L/16, ResNet-50. Self-distillation pretraining on 10,000+ WSIs.
**Input:** .svs, .tiff WSI files. Patch coordinates in .npy; features as .pt tensors.
**Preprocessing:** CLAM for tissue segmentation.
**Performance:** Classification accuracy 0.9511 on TCGA-RCC.

---

## NLP / Report Generation

### PULSE (Chinese Medical LLM)
**Repo:** https://github.com/openmedlab/PULSE
**Stars:** 494

**Sizes:** 7B and 20B parameters.
**Domain:** Chinese medical question answering, clinical decision support.
**Access:** HuggingFace (requires access request for 20B).
**Benchmark:** PULSE-Pro outperforms ChatGPT on 7 of 8 Chinese medical benchmarks.

---

### XrayPULSE (Multimodal Radiology Report Generation)
**Repo:** https://github.com/openmedlab/XrayPULSE
**Stars:** 178

**Architecture:**
```
Chest X-ray → MedCLIP visual encoder
            → Q-former adapter (BLIP2 style)
            → PULSE 7B LLM
            → Chinese radiology report text
```
**Input:** Chest X-ray image + optional Chinese text query.
**Output:** Chinese-language radiology report.
**Deployment:** Local bash script. No REST API.
**Relevance:** Architecture pattern for automated report generation feature.

---

### PULSE-EVAL (Medical LLM Benchmark)
**Repo:** https://github.com/openmedlab/PULSE-EVAL
**Stars:** 24

**Datasets evaluated (8):**
1. MedQA USMLE (English)
2. Chinese National Physician Exam
3. PromptCBLUE
4. WebMedQA
5. MedTriage
6. DialogSumm
7. MedicineQA
8. CheckupQA

**Evaluation methodology:** GPT-4 as adjudicator + ELO ranking + accuracy/BLEU/F1.
**Leaderboard:** GPT-4 > PULSE-Pro > ChatGPT > PULSE.

---

## Few-Shot / Adapter Framework

### MedFM (Foundation Model Challenge Framework)
**Repo:** https://github.com/openmedlab/MedFM
**Stars:** 264 | **Venue:** NeurIPS 2023

**Challenge tracks:**
- Few-shot adaptation (1/5/10-shot)
- Transfer learning

**Datasets:** ChestDR (chest X-ray), ColonPath (pathology), Endo (endoscopy).

**Backbones evaluated:**
- ViT variants: EVA02, DINOv2, CLIP
- Swin-B, DenseNet121, EfficientNet-B5

**Framework:** MMClassification / MMPreTrain (config-driven).
**Key insight:** Adapter-only fine-tuning with frozen backbone is competitive with full fine-tuning at low data regimes.
