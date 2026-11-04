"""HTTP API for the WeCure skin lesion research frontend."""

import base64
import io
import os

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

import fusion_utils as fu


MODEL_DIR = os.getenv("MODEL_DIR", "models")
DEVICE = os.getenv("MODEL_DEVICE", "cpu")
MAX_IMAGE_BYTES = 10 * 1024 * 1024
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "https://wecure-five.vercel.app")

app = FastAPI(
    title="WeCure Skin Cancer Research API",
    version="1.0.0",
    description="Research prototype for skin lesion image analysis. Not for clinical use.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

_models = None


def models():
    global _models
    if _models is None:
        try:
            _models = fu.load_models(MODEL_DIR, DEVICE)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Model files could not be loaded") from exc
    return _models


@app.get("/health")
def health():
    try:
        models()
    except HTTPException:
        return {"status": "unavailable", "model": "skin-cancer"}
    return {"status": "ok", "model": "skin-cancer", "classes": fu.CLASSES}


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
    if sex not in fu.SEXES or localization not in fu.LOCALIZATIONS:
        raise HTTPException(status_code=422, detail="Unsupported sex or lesion localization")

    resnet, backbone, fusion, preprocessor, cam = models()
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
