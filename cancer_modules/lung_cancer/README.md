# Multimodal AI for Personalized Cancer Diagnosis

WeCure includes the existing skin lesion research module and a lung cancer research
prototype with 2D image, clinical risk-level, and combined-workflow modules. The existing
Next.js frontend remains the UI for both modules.

The lung image classifier uses one 2D CT slice image (JPG/JPEG/PNG); it does not
accept a full CT volume or NIfTI file. Its model weights and the clinical CSV are
adapted from the public [Lung_Cancer_Streamlit reference repository](https://github.com/vedantkadam/Lung_Cancer_Streamlit).
The clinical output predicts that dataset's `Low`, `Medium`, or `High` label.
These outputs are research estimates, not cancer diagnoses.

## Existing Skin Module Method
- **Image model:** ResNet-18 (ImageNet pretrained), 7 classes
- **Clinical model:** MLP on age, sex and localization (19 encoded features, 32-d embedding)
- **Fusion model:** 512-d image features + 32-d clinical embedding, concatenated (544-d) and classified
- **Explainability:** Grad-CAM on ResNet-18 `layer4`
- **Split:** by `lesion_id` (no leakage), shared across all experiments (`data/split.csv`)
- **Imbalance:** class-weighted cross-entropy

## Existing Skin Module Results (test set, 1502 images)
| Model | Accuracy | Macro-F1 | Melanoma recall |
|---|---|---|---|
| Image only | 0.779 | 0.658 | 0.557 |
| Clinical only | 0.365 | 0.219 | 0.150 |
| Fusion | 0.812 | 0.718 | 0.647 |

Grad-CAM examples: `results/gradcam_examples.png`, `results/gradcam_errors.png`

## Run the Streamlit skin prototype (optional)
    pip install -r requirements.txt
    streamlit run app.py

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
cp .env.example .env.local
pnpm install
pnpm dev
```

On Windows PowerShell, use `Copy-Item .env.example .env.local` instead of `cp`. Run the backend in a separate terminal. For the local `.env.example` settings, start it on port 8001 and allow the local frontend origins:

```powershell
$env:TF_USE_LEGACY_KERAS="1"
$env:FRONTEND_ORIGIN="http://localhost:3000,http://127.0.0.1:3000"
uvicorn api:app --host 127.0.0.1 --port 8001
```

For the existing Vercel project, set **Root Directory** to `frontend` and add both `NEXT_PUBLIC_API_URL` and `LUNG_API_URL` with the deployed Render API base URL (for example, `https://your-api.onrender.com`, without `/health` or a trailing slash). `NEXT_PUBLIC_API_URL` connects the existing image and clinical screens; `LUNG_API_URL` is used by the same-origin proxy for Module 3. On the Render backend, set `FRONTEND_ORIGIN` to the deployed Vercel origin so the existing direct frontend requests pass CORS. Redeploy both services after changing environment variables. The frontend and backend share this repository, while Render can continue building the backend from the repository root.

The API is a research prototype. Its predictions must not be used for clinical diagnosis or treatment decisions.

## Lung Cancer Modules

- `GET /api/v1/lung/clinical-fields` lists the numeric fields used by the clinical form.
- `POST /api/v1/analysis/lung-cancer-image` accepts a multipart `file` image (JPG/JPEG/PNG).
- `POST /api/v1/analysis/lung-cancer-clinical` accepts JSON `{ "features": { ... } }` and returns the dataset's risk-level prediction.
- `POST /api/v1/analysis/lung-cancer-fusion` accepts a multipart `file` image and JSON `features` field, then returns both independent model outputs together.
- `models/lung_cancer/keras_model.h5` contains the referenced pretrained 2D image model; `data/lung_cancer/clinical.csv` contains the clinical rows used to fit the small prototype classifier.
- The clinical model uses an 80/20 stratified holdout for an exploratory metric. This is not independent clinical validation.
- The image folders do not have patient-level links to the clinical CSV, so Module 3 is a combined workflow and does not calculate a learned joint-fusion score.
- Install dependencies with Python 3.11 recommended, then run the API and frontend using the commands above.
- The frontend `.env.example` is a safe local template. Copy it to `.env.local`; keep `.env.local` local because it is ignored by Git.

## Repo structure
- `app.py`, `fusion_utils.py`: Streamlit app, model classes, Grad-CAM
- `api.py`: FastAPI backend for the frontend
- `frontend/`: Next.js WeCure web app
- `models/`: trained weights and preprocessor
- `results/`: metrics, predictions, confusion matrices, plots
- `notebooks/`: Kaggle notebooks (training and evaluation)
- `data/split.csv`: train/val/test split

## Data
- Skin module: HAM10000 (Kaggle: "Skin Cancer MNIST: HAM10000"). Images are not included in this repo.
- Lung modules: the small clinical CSV and pretrained 2D image weights adapted from the [Lung_Cancer_Streamlit reference repository](https://github.com/vedantkadam/Lung_Cancer_Streamlit). The lung image module accepts individual JPG/JPEG/PNG slices only.

## Team
Member 1: image classification | Member 2: clinical model | Member 3: fusion and evaluation | Member 4: Grad-CAM, app, integration

## Disclaimer
Research prototype for academic use. Not a medical device and not for clinical decisions.
