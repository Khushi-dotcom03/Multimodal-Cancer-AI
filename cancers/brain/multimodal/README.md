# Brain MRI + Clinical IDH Fusion

This package trains three patient-level research classifiers for IDH status: MRI-only, clinical-only, and learned MRI/clinical feature fusion. The fused classifier is trained on the concatenated embeddings from a frozen EfficientNet-B0 MRI encoder and a trainable clinical MLP. It does not average independent model predictions.

## Dataset layout and defaults

The current default paths in `config.py` point to:

```text
data/brain cancer/archive (2)/UTSW_Glioma_2D/dataset/BT0001/brain_t1ce/*.png
data/brain cancer/UTSW_Glioma_Metadata-2-1.tsv
weights/best_model.pth
```

The MRI folders are matched to the TSV using exact `BTxxxx` patient ID ↔ `Subject ID` equality. Only patients with readable T1CE images and a known `IDH` label (`mutated` or `wild type`) are eligible. At the audited run, 625 IDs matched across files; 3 had unknown IDH and 622 patients were used. Paths can be overridden without editing source:

```powershell
$env:BRAIN_MM_DATA_ROOT = 'D:\data\UTSW_Glioma_2D\dataset'
$env:BRAIN_MM_CLINICAL_FILE = 'D:\data\UTSW_Glioma_Metadata.tsv'
$env:BRAIN_MM_PRETRAINED_CHECKPOINT = 'D:\models\best_model.pth'
```

The CNN deterministically samples up to 8 evenly spaced T1CE PNG slices from each patient. It converts grayscale to three channels, resizes to 224×224, and applies ImageNet normalization. It uses the existing pretrained EfficientNet-B0 checkpoint as a frozen feature encoder; the original four-class head is discarded. Patient embeddings are the mean of that patient’s slice embeddings.

Clinical features are **Age at Imaging, Sex at birth, Tumor Grade, 1p19Q CODEL, and MGMT**. Numerical imputation/scaling and categorical imputation/one-hot encoding are fitted using training patients only. `IDH` is the target; `IDH_Testing Method`, `Subject ID`, and `Tumor Type` are excluded. Missing clinical measurements are imputed by the train-fitted pipeline.

## Train, validate, and evaluate

From the project root in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m cancers.brain.multimodal.train
```

The seed defaults to 42. By default, a stratified patient-level split allocates 70% to training, 15% to validation, and 15% to final test; it asserts that patient IDs do not overlap. The validation set selects checkpoints and early stopping. Test metrics are calculated only after all three model checkpoints have been selected. Class-weighted cross entropy addresses the target imbalance. Training prints data counts, extraction progress, per-epoch losses/scores, and final held-out metrics.

Optional controls:

```powershell
python -m cancers.brain.multimodal.train --epochs 60 --patience 10
python -m cancers.brain.multimodal.train --data-root 'D:\data\dataset' --clinical-file 'D:\data\metadata.tsv' --pretrained-checkpoint 'D:\weights\best_model.pth'
python -m cancers.brain.multimodal.train --force-features
```

MRI embeddings are cached under `artifacts/cache/` with a digest of patient paths, checkpoint metadata, and slice count. `--force-features` rebuilds that cache. To print the last saved evaluation summary without retraining:

```powershell
python -m cancers.brain.multimodal.evaluate
```

## Artifacts

Training writes only within this package:

- `artifacts/brain_idh_mri_best.pt`
- `artifacts/brain_idh_clinical_best.pt`
- `artifacts/brain_idh_fusion_best.pt`
- `artifacts/brain_idh_clinical_preprocessor.joblib`
- `artifacts/cache/` (frozen slice features)
- `reports/brain_idh_multimodal_metrics.json` (split, counts, model selection, per-class metrics, confusion matrices)
- `reports/model_comparison.csv`
- `reports/confusion_matrices.png`
- `reports/model_comparison.png`
- `reports/patient_splits.json`

## Inference

Python inference accepts a list of T1CE slice paths plus a clinical mapping:

```python
from cancers.brain.multimodal.inference import predict_patient
from cancers.brain.multimodal.config import DATA_ROOT

result = predict_patient("BT0001", DATA_ROOT, {
    "Age at Imaging": 44,
    "Sex at birth": "F",
    "Tumor Grade": 4,
    "1p19Q CODEL": "non co-deleted",
    "MGMT": None,
})
print(result)
```

The API router also exposes `POST /api/v1/cancers/brain/multimodal-idh-analysis`. Send one or more `files` form parts containing T1CE slices from the same patient, with optional `age_at_imaging`, `sex_at_birth`, `tumor_grade`, `codeletion_1p19q`, and `mgmt` fields. Scores are uncalibrated research outputs, not a medical diagnosis. The pre-existing `/multimodal-analysis` endpoint remains for frontend compatibility and is explicitly a legacy parallel-output endpoint, not the learned fusion model.

## Evaluation cautions

The saved test set is patient-disjoint but comes from the same single-source UTSW cohort. It is not external validation. `1p19Q CODEL` and tumor grade are pathology/molecular metadata and may not be available at the intended decision time; performance must be interpreted in that context. The MRI encoder is frozen and was pretrained for a different four-class MRI task. Scores are not calibrated, and the small held-out set makes them uncertain. These models are for research and education only.
