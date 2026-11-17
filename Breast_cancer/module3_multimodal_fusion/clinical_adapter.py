"""Structured wrapper for the saved Module 2 histologic-grade pipeline."""

from __future__ import annotations

from functools import lru_cache
from math import isfinite
from numbers import Real
from pathlib import Path
from typing import Any
from collections.abc import Mapping

import numpy as np
import pandas as pd


FEATURE_NAMES = (
    "Age at Diagnosis",
    "Tumor Size",
    "ER Status",
    "PR Status",
    "HER2 Status",
)
NUMERIC_FEATURES = ("Age at Diagnosis", "Tumor Size")
CATEGORICAL_FEATURES = ("ER Status", "PR Status", "HER2 Status")
GRADE_LABELS = {1: "Grade 1", 2: "Grade 2", 3: "Grade 3"}

MODULE2_DIR = Path(__file__).resolve().parent.parent / "module2_clinical_analysis"
MODEL_PATH = MODULE2_DIR / "clinical_grade_model.pkl"


def _result(
    *,
    status: str,
    predicted_grade: int | None = None,
    grade_label: str | None = None,
    message: str,
) -> dict[str, Any]:
    """Build a stable result shape without cancer probability or diagnosis."""
    return {
        "status": status,
        "predicted_grade": predicted_grade,
        "grade_label": grade_label,
        "message": message,
    }


@lru_cache(maxsize=1)
def _load_model() -> Any:
    """Load the trusted, serialized sklearn pipeline from Module 2."""
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Clinical grade model not found: {MODEL_PATH}")

    try:
        import joblib
    except Exception as exc:
        raise RuntimeError(
            "joblib could not be imported. It is required to load the clinical "
            f"model. Original error: {type(exc).__name__}: {exc}"
        ) from exc

    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:
        raise RuntimeError(
            "Could not load the clinical model. Check that joblib and the "
            "scikit-learn version are compatible with the saved pipeline. "
            f"Original error: {type(exc).__name__}: {exc}"
        ) from exc


def _is_missing(value: Any) -> bool:
    """Recognize scalar null values and blank strings without imputing them."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _validate_and_prepare(features: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Validate the exact feature mapping and prepare raw pipeline inputs."""
    provided_keys = set(features.keys())
    expected_keys = set(FEATURE_NAMES)
    missing_keys = [name for name in FEATURE_NAMES if name not in provided_keys]
    extra_keys = sorted(str(name) for name in provided_keys - expected_keys)
    if missing_keys or extra_keys:
        details = []
        if missing_keys:
            details.append("missing feature keys: " + ", ".join(missing_keys))
        if extra_keys:
            details.append("unexpected feature keys: " + ", ".join(extra_keys))
        return None, "Input must contain exactly the five model features (" + "; ".join(details) + ")."

    cleaned: dict[str, Any] = {}
    for name in NUMERIC_FEATURES:
        value = features[name]
        if _is_missing(value):
            cleaned[name] = np.nan
            continue
        if isinstance(value, bool) or not isinstance(value, Real):
            return None, f"{name} must be a numeric value or missing."
        numeric_value = float(value)
        if not isfinite(numeric_value):
            return None, f"{name} must be finite or missing."
        if name == "Age at Diagnosis" and not 0 <= numeric_value <= 120:
            return None, "Age at Diagnosis must be between 0 and 120."
        if name == "Tumor Size" and numeric_value < 0:
            return None, "Tumor Size must be zero or greater."
        cleaned[name] = numeric_value

    for name in CATEGORICAL_FEATURES:
        value = features[name]
        if _is_missing(value):
            # Pass missing values through; the saved sklearn pipeline imputes them.
            cleaned[name] = np.nan
            continue
        if not isinstance(value, str):
            return None, f"{name} must be 'Positive', 'Negative', or missing."
        value = value.strip()
        if value not in {"Positive", "Negative"}:
            return None, f"{name} must be 'Positive', 'Negative', or missing."
        cleaned[name] = value

    return cleaned, None


def predict_clinical_grade(features: Mapping[str, Any]) -> dict[str, Any]:
    """Predict Grade 1/2/3 from exactly the five raw Module 2 input features.

    Missing feature values are passed as NaN to the saved pipeline, whose
    fitted imputers handle them. This function returns a grade only; it does
    not generate a cancer probability or diagnosis.
    """
    if not isinstance(features, Mapping):
        return _result(
            status="invalid_input",
            message="Input must be a mapping with exactly the five named clinical features.",
        )

    cleaned, validation_error = _validate_and_prepare(features)
    if validation_error:
        return _result(status="invalid_input", message=validation_error)

    # Column order and names match the model-training notebook exactly.
    clinical_row = pd.DataFrame(
        [[cleaned[name] for name in FEATURE_NAMES]],
        columns=list(FEATURE_NAMES),
    )

    try:
        model = _load_model()
        grade = int(model.predict(clinical_row)[0])
    except FileNotFoundError as exc:
        return _result(status="model_unavailable", message=str(exc))
    except Exception as exc:
        return _result(
            status="prediction_error",
            message=f"Clinical grade prediction failed: {type(exc).__name__}: {exc}",
        )

    grade_label = GRADE_LABELS.get(grade)
    if grade_label is None:
        return _result(
            status="prediction_error",
            message=f"Saved model returned an unexpected grade value: {grade}.",
        )

    missing_features = [name for name in FEATURE_NAMES if _is_missing(features[name])]
    message = f"Clinical model predicted {grade_label}."
    if missing_features:
        message += (
            " Missing input values were passed to the saved pipeline's "
            "preprocessing steps."
        )
    return _result(
        status="success",
        predicted_grade=grade,
        grade_label=grade_label,
        message=message,
    )
