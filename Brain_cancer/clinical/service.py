"""Inference service for the IPD-Brain clinical glioma-subtype model."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from threading import Lock

import joblib
import pandas as pd

from Brain_cancer.clinical.pipeline import CLASSES, DISPLAY_CLASSES, FEATURE_COLUMNS, clean_site


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "brain_clinical_pipeline.joblib"
MODEL_NAME = "IPD-Brain Clinical Glioma Subtype Classifier"
DISCLAIMER = (
    "This is a research-oriented prediction for patients represented by the IPD-Brain glioma dataset. "
    "It is not a diagnosis and must not replace professional medical evaluation."
)


class BrainClinicalModelUnavailable(RuntimeError):
    """Raised when the saved, audited clinical model cannot be loaded."""


class BrainClinicalService:
    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path or os.getenv("BRAIN_CLINICAL_MODEL_PATH", DEFAULT_MODEL_PATH))
        self._artifact: dict | None = None
        self._lock = Lock()

    def load(self) -> dict:
        if self._artifact is not None:
            return self._artifact
        with self._lock:
            if self._artifact is not None:
                return self._artifact
            if not self.model_path.is_file():
                raise BrainClinicalModelUnavailable(f"Brain clinical model artifact not found: {self.model_path}")
            try:
                artifact = joblib.load(self.model_path)
                if not isinstance(artifact, dict) or "model" not in artifact or "metadata" not in artifact:
                    raise ValueError("Artifact does not contain a model and metadata")
                if not artifact["metadata"].get("deployment_eligible", False):
                    raise ValueError("Training evaluation did not exceed the majority-class baseline")
                if list(artifact["model"].classes_) != sorted(CLASSES):
                    raise ValueError("Saved model class set does not match the IPD-Brain target classes")
                self._artifact = artifact
            except Exception as exc:
                raise BrainClinicalModelUnavailable(f"Could not load Brain clinical model: {exc}") from exc
        return self._artifact

    def analyze(self, age: float, sex: str, site: str | None) -> dict:
        if not 5 <= float(age) <= 78:
            raise ValueError("Age must be between 5 and 78, the range represented in this dataset.")
        normalized_sex = str(sex).strip().upper()
        if normalized_sex not in {"M", "F"}:
            raise ValueError("Sex must be M or F.")
        if site is not None and len(site) > 160:
            raise ValueError("Site must be 160 characters or fewer.")

        artifact = self.load()
        features = pd.DataFrame([{
            "Age": float(age),
            "Sex": normalized_sex,
            "SITE": clean_site(site),
        }], columns=FEATURE_COLUMNS)
        model = artifact["model"]
        raw_scores = model.predict_proba(features)[0]
        class_order = list(model.classes_)
        scores = {label: float(raw_scores[class_order.index(label)]) for label in CLASSES}
        predicted = max(scores, key=scores.get)

        return {
            "analysisId": uuid.uuid4().hex,
            "predictedSubtype": predicted,
            "predictedSubtypeLabel": DISPLAY_CLASSES[predicted],
            "classScores": scores,
            "scoreType": "uncalibrated model scores",
            "model": {
                "name": MODEL_NAME,
                "architecture": "Balanced multinomial logistic regression",
                "dataset": "IPD-Brain clinical cohort",
                "features": FEATURE_COLUMNS,
                "target": "Glioma subtype",
                "testMetrics": artifact["metadata"]["test_metrics"]["selected_model"],
                "majorityBaseline": artifact["metadata"]["test_metrics"]["majority_class_baseline"],
                "validationMacroF1": artifact["metadata"]["model_selection"]["candidates"][artifact["metadata"]["model_selection"]["selected_model"]]["mean_macro_f1"],
            },
            "inputSummary": {
                "age": float(age),
                "sex": "Male" if normalized_sex == "M" else "Female",
                "site": site.strip() if site and site.strip() else "Not provided",
            },
            "disclaimer": DISCLAIMER,
            "inferenceStatus": "completed",
        }


service = BrainClinicalService()
