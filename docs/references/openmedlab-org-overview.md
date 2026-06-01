# OpenMEDLab GitHub Organization — Overview & Repository Index

> Source: https://github.com/openmedlab
> Gathered: 2026-03-18
> Organization: Shanghai AI Lab (pjlab.org.cn)
> Mission: "The world's first open-source platform for medical foundation models"
> Contact: openmedlab@pjlab.org.cn

---

## Organization Summary

OpenMEDLab develops and releases pre-trained foundation models across **10+ medical modalities**:
imaging (CT, MRI, X-ray, Ultrasound, Pathology/WSI, Retina, Endoscopy), NLP (Chinese medical LLMs),
bioinformatics, and protein analysis. All models are released under **CC-BY-NC 4.0** (non-commercial).

---

## Repository Index (30 public repos)

| Repository | Stars | Category | Description |
|---|---|---|---|
| [Awesome-Medical-Dataset](https://github.com/openmedlab/Awesome-Medical-Dataset) | 1,724 | Reference | Curated collection of medical dataset resources |
| [MedLSAM](https://github.com/openmedlab/MedLSAM) | 518 | Segmentation | Localize and Segment Anything Model for 3D medical images |
| [PULSE](https://github.com/openmedlab/PULSE) | 494 | NLP | Chinese medical language model (7B / 20B parameters) |
| [USFM](https://github.com/openmedlab/USFM) | 323 | Ultrasound | First ultrasound foundation model |
| [MedFM](https://github.com/openmedlab/MedFM) | 264 | Benchmark | NeurIPS 2023 few-shot/transfer learning challenge framework |
| [MIS-FM](https://github.com/openmedlab/MIS-FM) | 246 | CT Segmentation | 3D CT segmentation foundation model |
| [PathoDuet](https://github.com/openmedlab/PathoDuet) | 222 | Pathology | Foundation models for H&E and IHC histopathology |
| [Endo-FM](https://github.com/openmedlab/Endo-FM) | 218 | Endoscopy | Foundation model for endoscopy video analysis |
| [XrayPULSE](https://github.com/openmedlab/XrayPULSE) | 178 | Report Gen | Chest X-ray + multimodal conversational radiology assistant |
| [CITE](https://github.com/openmedlab/CITE) | 142 | Pathology | Text-guided pathological image classification |
| [MIU-VL](https://github.com/openmedlab/MIU-VL) | 137 | Vision-Language | Medical image understanding with VLMs |
| [DeblurringMIM](https://github.com/openmedlab/DeblurringMIM) | 131 | Ultrasound | Deblurring masked image modeling for thyroid ultrasound |
| [BROW](https://github.com/openmedlab/BROW) | 122 | Pathology/WSI | Whole slide image analysis via self-distillation |
| [STU-Net](https://github.com/openmedlab/STU-Net) | 115 | Segmentation | Largest pre-trained medical segmentation model (1.4B params) |
| [PRIME](https://github.com/openmedlab/PRIME) | 105 | Bioinformatics | Protein language model for thermostability prediction |
| [PULSE-COVID-19](https://github.com/openmedlab/PULSE-COVID-19) | 103 | NLP | COVID-19 variant of the PULSE language model |
| [RETFound_MAE](https://github.com/openmedlab/RETFound_MAE) | 102 | Retinal | Foundation model for retinal images (Nature 2023) |
| [BrainMVP](https://github.com/openmedlab/BrainMVP) | 81 | Brain MRI | Multi-modal MRI vision pre-training |
| [SAM-Med2D](https://github.com/openmedlab/SAM-Med2D) | 76 | Segmentation | SAM adapted for 2D medical image segmentation |
| [SAM-Med3D](https://github.com/openmedlab/SAM-Med3D) | 41 | Segmentation | Promptable 3D volumetric medical image segmentation |
| [Data-Centric-FM-Healthcare](https://github.com/openmedlab/Data-Centric-FM-Healthcare) | 29 | Research | Data-centric approaches for healthcare foundation models |
| [PULSE-EVAL](https://github.com/openmedlab/PULSE-EVAL) | 24 | Benchmark | Benchmark for medical language model evaluation |
| [dataset](https://github.com/openmedlab/dataset) | 21 | Datasets | Medical image dataset collection |
| [Swin-UMamba](https://github.com/openmedlab/Swin-UMamba) | 12 | Segmentation | Mamba-based UNet with Swin pretraining |
| [Axon-Seg](https://github.com/openmedlab/Axon-Seg) | 8 | Neuro | Whole-brain axon segmentation and circuitry profiling |
| [ProSST](https://github.com/openmedlab/ProSST) | 8 | Bioinformatics | Protein sequence and structure transformer |
| [A-Eval](https://github.com/openmedlab/A-Eval) | 4 | Benchmark | Cross-dataset benchmark for abdominal multi-organ segmentation |
| [Osteoarthritis-Benchmark](https://github.com/openmedlab/Osteoarthritis-Benchmark) | 4 | Benchmark | LLM benchmark for osteoarthritis knowledge |
| [BrainSCK](https://github.com/openmedlab/BrainSCK) | 3 | Neuro | Brain spatial causal knowledge |

---

## Modality Coverage Matrix

| Modality | Models |
|---|---|
| CT (3D) | STU-Net, MIS-FM, MedLSAM, A-Eval, Axon-Seg |
| MRI (brain) | BrainMVP, SAM-Med3D |
| X-ray (chest) | XrayPULSE, MedFM (ChestDR) |
| Ultrasound | USFM, DeblurringMIM |
| Pathology/WSI | PathoDuet, BROW, CITE |
| Endoscopy | Endo-FM, MedFM (Endo) |
| Retina | RETFound |
| 2D (multi-modal) | SAM-Med2D |
| NLP (Chinese medical) | PULSE, PULSE-COVID-19, PULSE-EVAL, XrayPULSE |

---

## License

All models: **CC-BY-NC 4.0** — non-commercial use only.
PULSE 7B/20B additionally requires HuggingFace model access request.
Commercial use requires a separate agreement with Shanghai AI Lab.
