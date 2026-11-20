"""HTTP API for the WeCure research frontend."""

import base64
import importlib
import io
import json
import os
import uuid
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

try:
    from . import lung_modules as lung
except ImportError:  # standalone: run uvicorn api:app from this directory
    from . import lung_modules as lung


MODEL_DIR = os.getenv("MODEL_DIR", "models")
DEVICE = os.getenv("MODEL_DEVICE", "cpu")
MAX_IMAGE_BYTES = 10 * 1024 * 1024
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "https://wecure-five.vercel.app")

app = FastAPI(
    title="WeCure Cancer Research API",
    version="1.1.0",
    description="Academic research prototype for skin and lung modules. Not for clinical use.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
router = APIRouter()

_models = None


def models():
    global _models
    if _models is None:
        try:
            fu = importlib.import_module("fusion_utils")
            _models = (fu, *fu.load_models(MODEL_DIR, DEVICE))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Model files could not be loaded") from exc
    return _models


@app.get("/health")
def health():
    skin_classes = None
    try:
        skin_classes = models()[0].CLASSES
    except HTTPException:
        pass
    modules = {
        "skin-cancer": "available" if skin_classes is not None else "unavailable",
        "lung-cancer-image": "available" if lung.IMAGE_MODEL_PATH.is_file() else "unavailable",
        "lung-cancer-clinical": "available" if lung.CLINICAL_DATA_PATH.is_file() else "unavailable",
        "lung-cancer-fusion": "available" if lung.IMAGE_MODEL_PATH.is_file() and lung.CLINICAL_DATA_PATH.is_file() else "unavailable",
    }
    response = {"status": "ok" if "available" in modules.values() else "unavailable", "modules": modules}
    if skin_classes is not None:
        response["classes"] = skin_classes
    return response


@router.get("/api/v1/lung/clinical-fields")
def lung_clinical_fields():
    return {
        "features": lung.CLINICAL_FEATURES,
        "scale": "Values follow the included dataset's coding; symptom and exposure values are dataset scores, not medical measurements.",
        "levels": ["Low", "Medium", "High"],
    }


def validate_lung_clinical_values(values):
    if not isinstance(values, dict):
        raise HTTPException(status_code=422, detail="Send a JSON object with a features object")
    if set(values) != set(lung.CLINICAL_FEATURES):
        raise HTTPException(status_code=422, detail="Provide exactly the clinical fields shown in the form")
    try:
        for feature in lung.CLINICAL_FEATURES:
            value = float(values[feature])
            lower, upper = (1, 100) if feature == "Age" else ((1, 2) if feature == "Gender" else (1, 5))
            if not lower <= value <= upper:
                raise ValueError(f"{feature} must be between {lower} and {upper}")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return values


@router.post("/api/v1/analysis/lung-cancer-clinical")
async def analyze_lung_clinical(payload: dict):
    values = payload.get("features") if isinstance(payload, dict) else None
    values = validate_lung_clinical_values(values)
    try:
        result = lung.predict_lung_clinical(values)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Lung clinical dataset is not installed") from exc
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "analysisId": uuid.uuid4().hex,
        "moduleId": "lung-cancer-clinical",
        "prediction": result["label"],
        "confidence": result["confidence"],
        "classification": result["classification"],
        "probabilities": result["probabilities"],
        "model": {
            "name": "Lung Clinical Risk-Level Classifier",
            "architecture": "Random Forest (trained from included CSV at first use)",
            "dataset": "Lung_Cancer_Streamlit clinical data.csv (1,000 rows)",
            "version": "prototype-1",
            "trainingStatus": "Trained on included dataset",
            "evaluationStatus": "80/20 stratified holdout; exploratory only",
            "lastUpdated": timestamp,
        },
        "createdAt": timestamp,
        "disclaimer": "Dataset risk-level estimate only; not a lung cancer diagnosis or medical advice.",
        "referenceHoldoutAccuracy": result["referenceHoldoutAccuracy"],
    }


@router.post("/api/v1/analysis/lung-cancer-fusion")
async def analyze_lung_fusion(file: UploadFile = File(...), features: str = Form(...)):
    """Run the available CT and clinical models independently in one request."""
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG or PNG CT slice image")
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be between 1 byte and 10 MB")
    try:
        clinical_values = validate_lung_clinical_values(json.loads(features))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Clinical features must be valid JSON") from exc
    try:
        with Image.open(io.BytesIO(content)) as uploaded_image:
            uploaded_image.verify()
        pil_image = Image.open(io.BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image") from exc
    try:
        image_result = lung.predict_lung_image(pil_image)
        clinical_result = lung.predict_lung_clinical(clinical_values)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Lung image model or clinical dataset is missing") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="One of the lung models could not process the request") from exc

    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "analysisId": uuid.uuid4().hex,
        "moduleId": "lung-cancer-fusion",
        "prediction": "Independent image and clinical outputs",
        "confidence": 0.0,
        "classification": "no-joint-score",
        "fusion": {
            "isJointModel": False,
            "image": image_result,
            "clinical": clinical_result,
        },
        "model": {
            "name": "Lung Image + Clinical Research Workflow",
            "architecture": "Independent CT CNN and clinical Random Forest",
            "dataset": "Separate, unlinked image and clinical datasets",
            "version": "prototype-1",
            "trainingStatus": "The two existing models are run independently",
            "evaluationStatus": "No patient-linked multimodal validation available",
            "lastUpdated": timestamp,
        },
        "createdAt": timestamp,
        "disclaimer": "These are independent research estimates. No joint fusion score is computed because the available datasets are not patient-linked.",
    }


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    age: str | None = Form(default=None),
    sex: str = Form(default="unknown"),
    localization: str = Form(default="unknown"),
):
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG or PNG image")

    content = await image.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be between 1 byte and 10 MB")
    try:
        pil_image = Image.open(io.BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image") from exc

    age_value = None
    if age not in (None, ""):
        try:
            age_value = float(age)
            if not 0 <= age_value <= 100:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Age must be between 0 and 100") from exc
    fu, resnet, backbone, fusion, preprocessor, cam = models()
    if sex not in fu.SEXES or localization not in fu.LOCALIZATIONS:
        raise HTTPException(status_code=422, detail="Unsupported sex or lesion localization")

    clinical = fu.clinical_vector(preprocessor, age_value, sex, localization)
    fused_probs, class_index, heatmap = fu.fusion_predict(
        pil_image, clinical, backbone, fusion, cam, DEVICE
    )
    image_probs = fu.image_only_probs(resnet, pil_image, DEVICE)

    overlay = Image.fromarray(fu.overlay(pil_image, heatmap))
    buffer = io.BytesIO()
    overlay.save(buffer, format="JPEG", quality=85)
    overlay_data_url = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    name = fu.CLASSES[class_index]
    return {
        "model": "multimodal-skin-lesion",
        "prediction": {"class": name, "label": fu.FULL_NAMES[name], "confidence": float(fused_probs[class_index])},
        "probabilities": {fu.CLASSES[i]: float(fused_probs[i]) for i in range(len(fu.CLASSES))},
        "imageOnlyProbabilities": {fu.CLASSES[i]: float(image_probs[i]) for i in range(len(fu.CLASSES))},
        "explanation": {"type": "grad-cam", "image": overlay_data_url},
        "disclaimer": "Academic research prototype only. Not for clinical diagnosis or treatment decisions.",
    }


@router.post("/api/v1/analysis/lung-cancer-image")
async def frontend_analysis(file: UploadFile = File(...)):
    """Match the multipart route and response shape used by the WeCure frontend."""
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG or PNG CT slice image")
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be between 1 byte and 10 MB")
    try:
        with Image.open(io.BytesIO(content)) as uploaded_image:
            uploaded_image.verify()
        pil_image = Image.open(io.BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image") from exc
    try:
        result = lung.predict_lung_image(pil_image)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Lung image model weights are not installed") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Lung image model could not process this image") from exc
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "analysisId": uuid.uuid4().hex,
        "moduleId": "lung-cancer-image",
        "prediction": result["label"],
        "confidence": result["confidence"],
        "classification": result["classification"],
        "probabilities": result["probabilities"],
        "model": {
            "name": "Lung CT Slice Classifier",
            "architecture": "CNN (pretrained Keras model)",
            "dataset": "Lung_Cancer_Streamlit repository image assets",
            "version": "prototype-1",
            "trainingStatus": "Pretrained weights supplied by reference repository",
            "evaluationStatus": "Independent validation not verified",
            "lastUpdated": timestamp,
        },
        "createdAt": timestamp,
        "disclaimer": "Research-only 2D slice estimate; not a diagnosis. This endpoint does not accept 3D CT volumes.",
    }

app.include_router(router)
