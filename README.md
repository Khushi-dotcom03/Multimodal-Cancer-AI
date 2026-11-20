# Multimodal Cancer AI Research Project

Four independent cancer research modules are grouped under `cancer_modules/`.
The project includes original module applications, models, assets, research data
and a shared Next.js frontend plus FastAPI backend. Research outputs are not
clinical diagnoses.

## Project structure

```text
cancer_modules/
  lung_cancer/       CT image, clinical and image-plus-clinical workflows
  breast_cancer/     Three existing image, clinical and evidence-review modules
  skin_cancer/       Branch backend plus preserved standalone implementation
  brain_cancer/      MRI, clinical and multimodal APIs and evaluation artifacts
frontend/            Common Next.js application for all four modules
api.py                Common FastAPI application
requirements.txt      Shared Python dependencies (user-maintained local edits preserved)
```

## Cancer modules

- **Lung Cancer:** `/lung` in the common frontend. Image, clinical and independent image-plus-clinical analysis use the existing Lung module API and models. The image model accepts 2D image slices only; it does not process 3D volumes.
- **Breast Cancer:** `/breast` links to the three existing Streamlit tools. Their outputs remain separate; the evidence-review module does not create a joint score.
- **Skin Cancer:** `/analysis` and the existing skin-specific pages use the Skin backend under `cancer_modules/skin_cancer/backend/`. The preserved earlier Streamlit implementation is under `cancer_modules/skin_cancer/standalone/`.
- **Brain Cancer:** `/brain-image`, `/brain-clinical`, and `/brain-multimodal` call the existing Brain APIs. The original MRI checkpoint and IPD-Brain CSV are not included and must be supplied locally.

## Method
- **Image model:** ResNet-18 (ImageNet pretrained), 7 classes
- **Clinical model:** MLP on age, sex and localization (19 encoded features, 32-d embedding)
- **Fusion model:** 512-d image features + 32-d clinical embedding, concatenated (544-d) and classified
- **Explainability:** Grad-CAM on ResNet-18 `layer4`
- **Split:** by `lesion_id` (no leakage), shared across all experiments (`data/split.csv`)
- **Imbalance:** class-weighted cross-entropy

## Results (test set, 1502 images)
| Model | Accuracy | Macro-F1 | Melanoma recall |
|---|---|---|---|
| Image only | 0.779 | 0.658 | 0.557 |
| Clinical only | 0.365 | 0.219 | 0.150 |
| Fusion | 0.812 | 0.718 | 0.647 |

Grad-CAM examples: `results/gradcam_examples.png`, `results/gradcam_errors.png`

## Run the common project

Install the shared requirements, then run the API from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn api:app --reload --port 8000
```

Run the shared frontend in a second terminal:

```powershell
cd frontend
pnpm install
pnpm dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in the frontend environment.
The Lung fusion page proxies to the same API by default; set `LUNG_API_URL` only
if the shared API uses a different address.

The Breast Cancer page links to the original Streamlit tools on ports 8501–8503.
Run each from its module folder, using `image_dashboard.py` (Module 1),
`breast_health_assessment.py` (Module 2), or `evidence_viewer.py` (Module 3).
Use the module-level requirements when a model's TensorFlow/PyTorch versions
conflict with another module; these stacks are not all compatible in one Python
environment.

Models are loaded from `models/` (`resnet18_best.pth`, `fusion_best.pth`, `clinical_preprocessor.joblib`).

## Connect the WeCure web frontend

The Next.js frontend is in `frontend/`. `api.py` provides the REST API:

```bash
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000
```

- `GET /health` reports whether the model loaded.
- `POST /api/analyze` accepts multipart form fields `image` (JPEG/PNG), optional `age`, `sex`, and `localization`. Metadata defaults to `unknown` when omitted.
- `POST /api/v1/analysis/skin-cancer` accepts the frontend's multipart `file` field and returns the result format it expects.
- The JSON response includes the fusion prediction, seven class probabilities, image-only probabilities, a Grad-CAM overlay data URL, and the research disclaimer.
- Set `FRONTEND_ORIGIN` to the deployed frontend origin and `MODEL_DIR` if the model files live elsewhere. The API keeps uploaded images in memory and does not save them.

Run the frontend locally from its folder:

```bash
cd frontend
pnpm install
pnpm dev
```

For the existing Vercel project, set **Root Directory** to `frontend` and add `NEXT_PUBLIC_API_URL` with the deployed Render API base URL (no trailing `/health`). Redeploy after changing the variable. The frontend and backend now share this repository, while Render can continue building the backend from the repository root.

The API is a research prototype. Its predictions must not be used for clinical diagnosis or treatment decisions.

## Model and data availability

The Brain module requires the original `best_model.pth` at
`cancer_modules/brain_cancer/weights/best_model.pth` and the clinical CSV at
`cancer_modules/brain_cancer/data/brain cancer/IPD_Brain.csv`. Neither is
included. Do not substitute fabricated weights or clinical data. Other modules
also depend on their own model files and datasets as described in their
module-specific READMEs.

## Data
HAM10000 (Kaggle: "Skin Cancer MNIST: HAM10000"). Images are not included in this repo.

## Team
Member 1: image classification | Member 2: clinical model | Member 3: fusion and evaluation | Member 4: Grad-CAM, app, integration

## Disclaimer
Research prototype for academic use. Not a medical device and not for clinical decisions.
# Brain MRI Image Analysis

The Brain Cancer image workflow is available at `/brain-image` and calls
`POST /api/v1/analysis/brain-tumour` on the existing FastAPI service. It reuses
the MIND EfficientNet-B0 model contract and class order: Glioma, Meningioma,
No Tumor, Pituitary Tumor. This is image-based research output only; it is not
a medical diagnosis.

## Model checkpoint

The service expects the original checkpoint at `Brain_cancer/weights/best_model.pth` by
default. Set `BRAIN_MRI_CHECKPOINT` to use another location. The checkpoint
must be the raw state dictionary from
[meolen07/mind-mri-brain-tumor](https://github.com/meolen07/mind-mri-brain-tumor),
and it is loaded strictly without changing the architecture. No checkpoint is
included in this working copy; inference returns HTTP 503 until the original
file is supplied. Do not substitute the skin model or an untrained network.

Checkpoint preprocessing follows the source inference code exactly: convert
to RGB, resize to 224 × 224, convert to tensor, then normalize with means
`[0.485, 0.456, 0.406]` and standard deviations `[0.229, 0.224, 0.225]`.
Inference applies softmax to the four model logits. These scores are not
calibrated probabilities. Grad-CAM is computed from EfficientNet-B0's final
feature block; if it fails, the class result is returned with Grad-CAM marked
unavailable.

## Run locally

From the repository root, activate the Python environment and run:

```powershell
$env:BRAIN_MRI_CHECKPOINT = "Brain_cancer/weights/best_model.pth"
$env:FRONTEND_ORIGIN = "http://localhost:3000"
uvicorn api:app --reload
```

Then in `frontend`, set `NEXT_PUBLIC_API_URL=http://localhost:8000` in the
environment and run `pnpm dev`. The existing skin route remains
`POST /api/v1/analysis/skin-cancer`.

## Brain Clinical Analysis

Clinical subtype analysis is available at `/brain-clinical`. It uses the
locally supplied `Brain_cancer/data/brain cancer/IPD_Brain.csv`, with the three `Subtype`
labels Glioblastoma, Astrocytoma, and Oligodendroglioma. The form/model schema
is Age, Sex, and optional Site. `C/F` and `Radiology` are excluded because
they contain prior/pathology subtype information in some records. Diagnosis,
WHO grade, subtype, and molecular markers are never model inputs.

Audit and reproduce training from the repository root:

```powershell
.\.venv\Scripts\python.exe -m Brain_cancer.clinical.audit
.\.venv\Scripts\python.exe -m Brain_cancer.clinical.train
```

The saved model and preprocessing pipeline are in
`Brain_cancer/clinical/artifacts/brain_clinical_pipeline.joblib`; aggregate
audit and evaluation results are in `Brain_cancer/evaluation/brain_clinical_dataset_audit.json`
and `Brain_cancer/evaluation/brain_clinical_metrics.json`. The JSON inference endpoint is
`POST /api/v1/cancers/brain/clinical-analysis`. Class scores are uncalibrated
model outputs. This module classifies subtypes among represented glioma cases;
it does not detect brain tumors or distinguish healthy people from patients.
