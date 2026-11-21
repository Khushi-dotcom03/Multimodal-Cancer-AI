"""Independent Module 1 and Module 2 inference for Breast Module 3.

No cancer fusion score is returned because no verified training cohort in this
project links the BUSI images with the exact five Module 2 clinical features.
"""

from __future__ import annotations

import io
import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from PIL import Image, UnidentifiedImageError

from cancer_modules.breast_cancer.module3_multimodal_fusion.clinical_adapter import (
    FEATURE_NAMES as MODULE2_FEATURE_NAMES,
    predict_clinical_grade,
)
from cancer_modules.breast_cancer.module3_multimodal_fusion.image_adapter import predict_ultrasound

router = APIRouter()
MAX_IMAGE_BYTES = 10 * 1024 * 1024
RESEARCH_DISCLAIMER = (
    "Module 3 shows separate research outputs from Module 1 and Module 2. "
    "It does not produce a combined cancer prediction or medical diagnosis."
)
NO_VALID_FUSION_REASON = (
    "No verified patient-linked training data in this project contains BUSI ultrasound, "
    "all five Module 2 clinical inputs, and benign/malignant ground truth. The BrEaST "
    "dataset has different clinical fields. Module 2 histologic grade is not cancer probability."
)


def _clinical_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": result.get("status", "prediction_error"),
        "predictedGrade": result.get("predicted_grade"),
        "predictedGradeLabel": result.get("grade_label"),
        "message": result.get("message", "Clinical grade result unavailable."),
        "disclaimer": (
            "Research-only histologic-grade estimate. It is not a cancer screening result, "
            "medical diagnosis, or treatment recommendation."
        ),
    }


def _image_result(result: dict[str, Any]) -> dict[str, Any]:
    prediction = result.get("prediction")
    return {
        "status": result.get("status", "prediction_error"),
        "prediction": prediction,
        "confidence": result.get("confidence"),
        "probabilities": result.get("class_probabilities", {"Normal": None, "Benign": None, "Malignant": None}),
        "inferenceStatus": result.get("status"),
        "validatorProbability": result.get("validator_probability"),
        "message": result.get("message", "Ultrasound image result unavailable."),
        "disclaimer": "Research-only BUSI ultrasound image classifier output; not a diagnosis.",
    }


@router.post("/api/v1/analysis/breast-cancer-fusion")
async def breast_cancer_fusion(
    file: UploadFile = File(...),
    features: str = Form(...),
) -> dict[str, Any]:
    """Run the same independent inference functions used by Modules 1 and 2."""
    analysis_id = uuid.uuid4().hex

    # Keep image-side validation/inference independent of the clinical prediction.
    image_output: dict[str, Any]
    content_type_ok = file.content_type in {"image/jpeg", "image/png"}
    if not content_type_ok:
        image_output = {"status": "invalid_image", "message": "Upload a JPG, JPEG, or PNG ultrasound image."}
    else:
        content = await file.read(MAX_IMAGE_BYTES + 1)
        if not content or len(content) > MAX_IMAGE_BYTES:
            image_output = {"status": "invalid_image", "message": "Image must be between 1 byte and 10 MB."}
        else:
            try:
                with Image.open(io.BytesIO(content)) as image:
                    if image.format not in {"JPEG", "PNG"}:
                        raise UnidentifiedImageError("Unsupported image format")
                    image.verify()
                temp_path: Path | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=".png" if file.content_type == "image/png" else ".jpg",
                        delete=False,
                    ) as temp_image:
                        temp_image.write(content)
                        temp_path = Path(temp_image.name)
                    image_output = predict_ultrasound(temp_path)
                finally:
                    if temp_path is not None:
                        temp_path.unlink(missing_ok=True)
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                image_output = {"status": "invalid_image", "message": f"The uploaded file is not a valid image: {exc}"}
            except Exception as exc:
                image_output = {"status": "prediction_error", "message": f"Image inference failed: {type(exc).__name__}: {exc}"}

    # Pass through the exact Module 2 feature names and values to its existing adapter.
    try:
        parsed_features = json.loads(features)
    except (TypeError, json.JSONDecodeError):
        parsed_features = None
    if isinstance(parsed_features, dict):
        clinical_output = predict_clinical_grade(parsed_features)
    else:
        clinical_output = {
            "status": "invalid_input",
            "message": "Clinical input must be a JSON object containing exactly the five Module 2 fields: "
            + ", ".join(MODULE2_FEATURE_NAMES)
            + ".",
        }

    image_result = _image_result(image_output)
    clinical_result = _clinical_result(clinical_output)
    branch_statuses = {image_result["status"], clinical_result["status"]}
    overall_status = "success" if branch_statuses <= {"success", "uncertain"} else "partial"
    return {
        "analysisId": analysis_id,
        "moduleId": "breast-cancer-combined-analysis",
        "status": overall_status,
        "imageResult": image_result,
        "clinicalResult": clinical_result,
        "fusionResult": {
            "status": "unavailable",
            "prediction": None,
            "score": None,
            "reason": NO_VALID_FUSION_REASON,
        },
        "model": {
            "image": "Existing Module 1 BUSI validator and MobileNetV2 inference pipeline",
            "clinical": "Existing Module 2 saved sklearn preprocessing and histologic-grade pipeline",
            "fusion": "Not trained; no compatible paired dataset has been verified",
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "disclaimer": RESEARCH_DISCLAIMER,
    }
