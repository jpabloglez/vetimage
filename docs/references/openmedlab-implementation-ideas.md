# OpenMEDLab Research → Platform Implementation Ideas

> Gathered: 2026-03-18
> Purpose: Actionable ideas derived from OpenMEDLab org research for the OpenMedLab platform
> Platform stack: Django 5 + DRF · React 18 + TypeScript · Celery · gRPC Orchestrator · PostgreSQL · Redis

---

## Priority Matrix

| Idea | Effort | Impact | Relevant Phase |
|---|---|---|---|
| nnU-Net universal connector | Medium | High | Phase 6 / AI Models |
| DICOM → NIfTI gateway hardening | Low | High | Phase 3 (done as prep) |
| DICOM SEG round-trip (seg → OHIF overlay) | High | High | Phase 6 |
| Organ label taxonomy in model registry | Low | Medium | Phase 5 |
| Automated report generation (XrayPULSE pattern) | High | High | Phase 6 |
| Few-shot adapter fine-tuning workflow | High | Medium | Future |
| WSI / DICOM WSI modality support | High | Medium | Future |
| Model benchmarking / QA module | Medium | Medium | Phase 6 |
| Segmentation result visualization | Medium | High | Phase 6 |

---

## Idea 1 — nnU-Net Universal AI Connector

**Source:** STU-Net, MIS-FM, A-Eval, Axon-Seg (all built on nnU-Net)

**Observation:** The majority of OpenMEDLab segmentation models use nnU-Net as their inference backend.
The CLI is uniform:
```bash
nnUNet_predict -i <input> -o <output> -t <task_id> -m 3d_fullres [-chk <checkpoint>]
```

**Implementation idea:**
Create a single `NNUNetConnector` class in `ai_analysis/connectors/nnunet.py`:
```python
class NNUNetConnector(BaseAIConnector):
    def prepare_input(self, task):
        # DICOM → NIfTI via dcm2niix (reuse FastSurfer pattern)

    def dispatch_job(self, task):
        # subprocess.run(['nnUNet_predict', '-i', ..., '-t', task.model.task_id, ...])
        # Store output NIfTI path in task.result_file_path

    def parse_output(self, output_dir):
        # Return segmentation mask paths + label metadata
```

Add `task_id` and `nnunet_config` fields to `AIModel` metadata. Models STU-Net-S/B/L/H, MIS-FM,
and A-Eval can all be registered as `AIModel` rows pointing to the same connector class with
different `task_id` values.

**No gRPC orchestrator needed** — nnU-Net is a local subprocess, same pattern as FastSurfer's
`prepare_input()` using dcm2niix.

---

## Idea 2 — DICOM SEG Round-Trip (Segmentation → OHIF Overlay)

**Source:** STU-Net, SAM-Med2D, MedLSAM outputs (NIfTI masks / NPZ arrays)

**Observation:** All segmentation models output NIfTI (.nii.gz) or NPZ masks. Currently these are
exposed as downloadable file links. Users cannot visualize overlays in the OHIF viewer.

**Implementation idea:**
After a segmentation task completes, add a post-processing Celery task:
```python
@app.task(queue='default')
def convert_seg_to_dicom_seg(task_id):
    task = AnalysisTask.objects.get(id=task_id)
    nifti_mask = task.result_file_path           # e.g. media/fastsurfer/seg.nii.gz
    source_dicom_series = task.input_image.series

    # Use highdicom or pydicom-seg to create a DICOM SEG object
    seg_dcm = create_dicom_seg(nifti_mask, source_dicom_series, label_map=task.model.label_map)

    # Store in Orthanc so OHIF viewer can render the overlay
    orthanc_client.upload(seg_dcm)
    task.result_metadata['dicom_seg_series_uid'] = seg_dcm.SeriesInstanceUID
    task.save()
```

Frontend: After task COMPLETED, show "View in Viewer" button that opens OHIF with the
`SeriesInstanceUID` of the SEG object pre-loaded as an overlay.

**Libraries:** `highdicom` (modern) or `pydicom-seg` (simpler).

---

## Idea 3 — Organ Label Taxonomy in AIModel Registry

**Source:** A-Eval's 8-organ cross-dataset taxonomy, TotalSegmentator's 104-organ `label_orders.json`

**Observation:** Segmentation models produce integer-labeled masks (e.g. label 1 = liver,
label 2 = spleen). Without a label map, results are uninterpretable.

**Implementation idea:**
Add a `label_map` JSON field to `AIModel`:
```python
label_map = models.JSONField(
    default=dict,
    help_text='Mapping from integer label to anatomy name, e.g. {"1": "liver", "2": "spleen"}'
)
```

The `ReportBuilder` service can then produce structured findings from segmentation results:
```python
# Instead of: "Segmentation completed, 5 labels found"
# Generate:   "Liver: 1,245 cm³ | Spleen: 187 cm³ | Right kidney: 142 cm³"
```

TotalSegmentator label map (104 organs) is available at:
https://github.com/wasserth/TotalSegmentator/blob/master/totalsegmentator/map_to_binary.py

---

## Idea 4 — Automated Radiology Report Generation (XrayPULSE Pattern)

**Source:** XrayPULSE (MedCLIP + Q-former + PULSE LLM)

**Architecture pattern:**
```
DICOM image → resize/normalize → Visual encoder (MedCLIP / BioViL-T)
                               → Q-former adapter (cross-attention bridge)
                               → LLM (PULSE / Llama-Med / Meditron)
                               → Draft report text
```

**Implementation idea for the Reports module:**
1. After AI analysis completes (especially for chest X-ray models like CheXNet),
   add an optional "Generate Draft Report" button.
2. The Celery task calls a report-gen microservice:
   ```python
   class ReportGenConnector(BaseAIConnector):
       def dispatch_job(self, task):
           image_b64 = encode_dicom_thumbnail(task.input_image)
           response = requests.post(self.endpoint_url, json={
               "image": image_b64,
               "modality": task.input_image.series.modality,
               "findings": task.result_metadata.get("findings", {}),
           })
           return response.json()["report_text"]
   ```
3. The draft text pre-fills the `Report.content.findings` field.
4. A radiologist reviews and finalizes (`status: DRAFT → FINAL`).

**Open-source LLM options (non-CC-BY-NC):**
- Meditron-7B (EPFL, Apache 2.0)
- BioMistral-7B (Apache 2.0)
- OpenBioLLM-8B (LLaMA-3 base, CC-BY-NC-4.0)

---

## Idea 5 — Few-Shot Adapter Fine-Tuning Workflow

**Source:** MedFM (NeurIPS 2023) — 1/5/10-shot adaptation with frozen backbone + lightweight adapters

**Observation:** MedFM shows that clinicians can adapt a foundation model to their institution's
specific pathology/protocol with as few as 1–10 labeled examples by only training adapter layers.

**Implementation idea:**
Add a "Fine-tune" tab to the AIModel detail page:
1. User uploads a small labeled dataset (images + labels, ZIP).
2. A Celery task runs adapter-only training:
   ```python
   @app.task(queue='ai_jobs')
   def run_adapter_finetuning(base_model_key, dataset_zip_path, num_shots, user_id):
       # Unzip, validate format (NIfTI + label file)
       # Run MedFM-style adapter training
       # Register new AIModel row with parent_model=base_model_key
   ```
3. The fine-tuned model appears in the registry as a derived model.
4. Training progress streamed via existing WebSocket consumer.

**Technical path:** MMPreTrain framework (used by MedFM) supports config-driven adapter
training without modifying base model weights.

---

## Idea 6 — WSI (Whole Slide Image) Modality Support

**Source:** PathoDuet, BROW, CITE — all operate on .svs/.tiff pathology slides

**Observation:** WSI files are increasingly wrapped in DICOM WSI objects (SOP Class
1.2.840.10008.5.1.4.1.1.77.1.6). Adding WSI support to the DICOM Gateway would unlock
the entire OpenMEDLab pathology model category.

**Implementation steps:**
1. DICOM Gateway: add WSI SOP class acceptance in C-STORE.
2. Storage: large WSI files (1–10GB) need S3-compatible object storage (Phase 6 roadmap item).
3. Viewer: OHIF v3 has basic DICOM WSI support; tile-serving endpoint needed.
4. AI connector: WSI models expect .svs/.tiff — add a DICOM WSI → TIFF extraction step
   (using `wsidicomizer` or `openslide`).

---

## Idea 7 — Model Benchmarking / QA Module

**Source:** A-Eval (segmentation), PULSE-EVAL (NLP) — both provide structured eval frameworks

**A-Eval methodology:**
- Upload ground-truth NIfTI label masks (de-identified)
- Run model prediction
- Compute DSC and NSD per organ
- Track results in a benchmark table

**PULSE-EVAL methodology:**
- Define evaluation questions + expected answers
- Run model inference
- Use GPT-4 or rule-based scoring as adjudicator

**Implementation idea for the platform:**
Add a `ModelBenchmark` model and associated Celery task:
```python
class ModelBenchmark(models.Model):
    ai_model = models.ForeignKey(AIModel, ...)
    dataset_name = models.CharField(max_length=100)
    metric_name = models.CharField(max_length=50)  # e.g. 'DSC', 'NSD', 'accuracy'
    score = models.FloatField()
    num_samples = models.IntegerField()
    evaluated_at = models.DateTimeField(auto_now_add=True)
    evaluated_by = models.ForeignKey(User, ...)
    notes = models.TextField(blank=True)
```

Expose via `/api/ai-analysis/models/{key}/benchmarks/` and display in the Model Details page.
Useful for verifying model quality before enabling for clinical research use.

---

## Idea 8 — NIfTI/BIDS as Standard Internal Exchange Format

**Source:** All OpenMEDLab models consume NIfTI; the BIDS naming convention is widely used

**Observation:** The existing OMLAB-012 anonymization module already produces NIfTI+BIDS ZIPs.
Every OpenMEDLab model expects NIfTI input. The dcm2niix subprocess (already used in the
FastSurfer and BIDS-anonymizer connectors) is the universal DICOM→NIfTI bridge.

**Implication:**
The `prepare_input()` hook in `BaseAIConnector` should become the **canonical DICOM→NIfTI
conversion point** for all future connectors. The current FastSurfer implementation should be
refactored into a shared utility:
```python
# ai_analysis/connectors/utils.py
def dicom_series_to_nifti(series, output_dir: Path, stem: str) -> list[Path]:
    """
    DICOM series → NIfTI via dcm2niix.
    Returns list of produced .nii.gz files.
    Reuses bids_utils.run_dcm2niix() from the anonymization module.
    """
    from dicom_images.services.bids_utils import run_dcm2niix
    dicom_dir = write_dicoms_to_tmpdir(series)
    return run_dcm2niix(dicom_dir, output_dir, stem)
```

This eliminates duplicated dcm2niix subprocess code across connectors.

---

## Idea 9 — Anonymization as a Mandatory Pre-processing Gate

**Source:** Awesome-Medical-Dataset — clinical datasets (FLARE22, AMOS, BTCV) all underwent
DICOM de-identification before being used to train OpenMEDLab models.

**Observation:** The anonymization module (OMLAB-012) is not just a tool — it is the **required
first step** before any study can be exported to an AI model or external system.

**Implementation idea:**
Add an optional enforcement flag at the `AIModel` level:
```python
requires_anonymization = models.BooleanField(
    default=False,
    help_text='If True, study must be anonymized before dispatch to this model.'
)
```

In `ai_analysis/views.py` `create()`:
```python
if task.model.requires_anonymization:
    anon_job = AnonymizationJob.objects.filter(
        study=task.input_image.series.study,
        status='COMPLETED',
        profile__in=['full', 'research'],
    ).first()
    if not anon_job:
        raise ValidationError(
            "This model requires the study to be anonymized first. "
            "Run a Full or Research profile anonymization job."
        )
```

---

## Idea 10 — Multi-Parametric MRI Support (BrainMVP Pattern)

**Source:** BrainMVP — pre-trained on 16,022 multi-parametric MRI (mpMRI) scans with
cross-modal reconstruction

**Observation:** Multi-parametric MRI (T1, T2, FLAIR, DWI, ADC within the same study)
is a common clinical protocol. The platform currently treats each series independently.
The PICAI connector already requires an `adc_image_id` alongside the main image,
showing a multi-input pattern.

**Implementation idea:**
Extend `CreateTaskRequest` and the `AnalysisTask` model to support **multiple input images**:
```python
# In AnalysisTask model:
input_images = models.ManyToManyField(
    MedicalImage,
    related_name='analysis_tasks',
    blank=True,
)
input_image = models.ForeignKey(...)  # keep for backward compat (primary image)
```

The `AIModel.required_parameters` schema can specify additional modalities:
```json
{
  "t2w_image_id": { "type": "integer", "description": "T2W series image ID", "required": true },
  "adc_image_id":  { "type": "integer", "description": "ADC map image ID",   "required": true }
}
```

This generalises the existing PICAI `adc_image_id` hack into a first-class multi-input API.
