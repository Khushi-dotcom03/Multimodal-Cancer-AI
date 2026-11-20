"""API for the saved Breast Cancer Module 2 clinical grade model."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from cancer_modules.breast_cancer.module3_multimodal_fusion.clinical_adapter import (
    predict_clinical_grade,
)

router = APIRouter()
FEATURE_NAMES = (
    "Age at Diagnosis",
    "Tumor Size",
    "ER Status",
    "PR Status",
    "HER2 Status",
)


@router.post("/api/v1/analysis/breast-clinical-grade")
def breast_clinical_grade(payload: dict):
    """Predict histologic grade using Module 2's saved sklearn pipeline."""
    features = payload.get("features") if isinstance(payload, dict) else None
    result = predict_clinical_grade(features)
    if result["status"] == "invalid_input":
        raise HTTPException(status_code=422, detail=result["message"])
    if result["status"] != "success":
        status_code = 503 if result["status"] == "model_unavailable" else 500
        raise HTTPException(status_code=status_code, detail=result["message"])

    return {
        "analysisId": uuid.uuid4().hex,
        "status": result["status"],
        "predictedGrade": result["predicted_grade"],
        "predictedGradeLabel": result["grade_label"],
        "message": result["message"],
        "model": {
            "name": "Breast Clinical Histologic Grade Classifier",
            "architecture": "Random Forest with saved sklearn preprocessing pipeline",
            "dataset": "Breast Module 2 clinical dataset",
            "version": "clinical_grade_model.pkl",
            "trainingStatus": "Trained model loaded from the existing Module 2 artifact",
            "evaluationStatus": "Reported test accuracy 51.26%; macro F1 0.4386; cross-validation macro F1 0.4899",
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        },
        "disclaimer": (
            "Research-only histologic-grade estimate among records similar to the training dataset. "
            "It is not a cancer screening result, medical diagnosis, or treatment recommendation."
        ),
    }
