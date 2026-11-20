"""FastAPI endpoint for the existing BUSI image-analysis models."""

import io
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from cancer_modules.breast_cancer.module3_multimodal_fusion.image_adapter import (
    predict_ultrasound,
)

router = APIRouter()
MAX_IMAGE_BYTES = 10 * 1024 * 1024


@router.post("/api/v1/analysis/breast-cancer-image")
async def breast_image_analysis(file: UploadFile = File(...)):
    """Validate and classify one BUSI ultrasound image using the saved models."""
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Upload a JPG, JPEG, or PNG ultrasound image.")

    content = await file.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be between 1 byte and 10 MB.")

    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {"JPEG", "PNG"}:
                raise HTTPException(status_code=415, detail="The uploaded file is not a JPG or PNG image.")
            image.verify()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from exc

    suffix = ".png" if file.content_type == "image/png" else ".jpg"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_image:
            temp_image.write(content)
            temp_path = Path(temp_image.name)
        outcome = predict_ultrasound(temp_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    status = outcome["status"]
    if status == "invalid_image":
        raise HTTPException(status_code=400, detail=outcome["message"])
    if status in {"model_unavailable", "dependency_unavailable", "model_error", "prediction_error"}:
        raise HTTPException(status_code=503, detail=outcome["message"])
    if status == "rejected":
        raise HTTPException(status_code=422, detail=outcome["message"])
    if status not in {"success", "uncertain"}:
        raise HTTPException(status_code=503, detail="The BUSI image model returned an unsupported result.")

    prediction = outcome["prediction"] or "Uncertain"
    return {
        "analysisId": uuid.uuid4().hex,
        "moduleId": "breast-cancer-image",
        "prediction": prediction,
        "confidence": outcome["confidence"] or 0.0,
        "classification": prediction,
        "probabilities": outcome["class_probabilities"],
        "model": {
            "name": "BUSI Ultrasound Classifier",
            "architecture": "MobileNetV2 with ultrasound validation model",
            "dataset": "BUSI",
            "version": "Module 1 saved Keras models",
            "trainingStatus": "Pretrained Module 1 models",
            "evaluationStatus": "Research prototype; external validation not established",
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "inferenceStatus": status,
        "validatorProbability": outcome["validator_probability"],
        "disclaimer": "Experimental BUSI ultrasound image classification for research only. It is not a medical diagnosis.",
    }
