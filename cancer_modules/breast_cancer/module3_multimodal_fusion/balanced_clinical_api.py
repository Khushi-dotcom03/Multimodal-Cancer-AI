"""Small local API exposing a validated, class-balanced grade candidate."""

from __future__ import annotations

import uuid
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException

from cancer_modules.breast_cancer.module3_multimodal_fusion.clinical_adapter import (
    FEATURE_NAMES,
    GRADE_LABELS,
    _validate_and_prepare,
)

ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "clinical_grade_balanced_candidate.pkl"
EVALUATION = Path(__file__).resolve().parent / "reports" / "clinical_grade_balanced_candidate.json"
app = FastAPI(title="Breast Clinical Grade Candidate API", version="1.0.0")


@lru_cache(maxsize=1)
def load_candidate():
    if not ARTIFACT.is_file():
        raise FileNotFoundError(f"Balanced grade candidate is missing: {ARTIFACT}")
    return joblib.load(ARTIFACT)


@app.post("/api/v1/analysis/breast-clinical-grade")
def breast_clinical_grade(payload: dict):
    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, dict):
        raise HTTPException(status_code=422, detail="Request must contain a features object.")
    cleaned, error = _validate_and_prepare(features)
    if error:
        raise HTTPException(status_code=422, detail=error)

    row = pd.DataFrame([[cleaned[name] for name in FEATURE_NAMES]], columns=list(FEATURE_NAMES))
    try:
        model = load_candidate()
        grade = int(model.predict(row)[0])
        vote_shares = [
            {"grade": int(label), "voteShare": float(score)}
            for label, score in zip(model.classes_, model.predict_proba(row)[0])
        ]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Balanced candidate unavailable: {type(exc).__name__}: {exc}") from exc
    label = GRADE_LABELS.get(grade)
    if label is None:
        raise HTTPException(status_code=500, detail=f"Candidate returned unsupported grade {grade}.")
    evaluation = json.loads(EVALUATION.read_text(encoding="utf-8"))
    cv = evaluation["patient_grouped_stratified_cv"]
    return {
        "analysisId": uuid.uuid4().hex,
        "status": "success",
        "predictedGrade": grade,
        "predictedGradeLabel": label,
        "message": f"Class-balanced research model predicted {label}.",
        "gradeScores": vote_shares,
        "evaluation": {
            "accuracy": cv["mean_accuracy"],
            "macroF1": cv["mean_macro_f1"],
            "recallByGrade": cv["mean_recall_by_grade"],
            "method": "5-fold stratified patient-grouped cross-validation",
        },
        "model": {
            "name": "Breast Clinical Histologic Grade Classifier (class-balanced candidate)",
            "architecture": "Class-balanced Random Forest with saved sklearn preprocessing pipeline",
            "dataset": "Breast Module 2 clinical dataset",
            "version": "clinical_grade_balanced_candidate.pkl",
            "trainingStatus": "Candidate trained using the existing Module 2 inputs and labels",
            "evaluationStatus": "Patient-grouped cross-validation; retrospective research only",
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        },
        "disclaimer": "Research-only histologic-grade estimate. It is not a cancer screening result, medical diagnosis, or treatment recommendation.",
    }
