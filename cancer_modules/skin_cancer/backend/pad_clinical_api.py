
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import joblib
import pandas as pd
import torch
from fastapi import APIRouter, Form, HTTPException

try:
    from . import config
    from .models.pad_clinical_model import PADClinicalMLP
except ImportError:
    import config
    from models.pad_clinical_model import PADClinicalMLP

logger = logging.getLogger(__name__)


router = APIRouter(tags=["pad-clinical"])

PAD_DIR = config.MODEL_DIR / "pad_ufes20"
CHECKPOINT = PAD_DIR / "clinical_best.pth"
PREPROCESSOR_FILE = PAD_DIR / "clinical_preprocessor.joblib"
LABELS_FILE = PAD_DIR / "clinical_labels.json"

FEATURES = [
    "age", "region", "itch", "grew",
    "hurt", "changed", "bleed", "elevation",
]

SUPPORTED_REGIONS = frozenset({
    "ABDOMEN", "ARM", "BACK", "CHEST", "EAR", "FACE", "FOOT", "FOREARM",
    "HAND", "LIP", "NECK", "NOSE", "SCALP", "THIGH",
})

_model = None
_preprocessor = None
_labels = None


def _load_pad_model():
    global _model, _preprocessor, _labels

    if _model is not None:
        return _model, _preprocessor, _labels

    try:
        for path in (CHECKPOINT, PREPROCESSOR_FILE, LABELS_FILE):
            if not path.is_file():
                raise FileNotFoundError(
                    f"Required PAD artifact missing: {path.name}"
                )

        preprocessor = joblib.load(PREPROCESSOR_FILE)

        with LABELS_FILE.open("r", encoding="utf-8") as file:
            labels = json.load(file)

        checkpoint = torch.load(
            CHECKPOINT,
            map_location=config.DEVICE,
            weights_only=True,
        )

        if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
            raise ValueError("Unexpected PAD checkpoint format.")

        input_features = int(checkpoint["input_features"])
        num_classes = int(checkpoint["num_classes"])

        if input_features != len(preprocessor.get_feature_names_out()):
            raise ValueError(
                "Checkpoint and preprocessor feature counts do not match."
            )

        if num_classes != len(labels):
            raise ValueError("Checkpoint and label counts do not match.")

        model = PADClinicalMLP(
            input_features=input_features,
            num_classes=num_classes,
        )

        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        model = model.to(config.DEVICE).eval()

        _model = model
        _preprocessor = preprocessor
        _labels = labels

        return _model, _preprocessor, _labels

    except Exception as exc:
        logger.exception("PAD clinical model loading failed")
        raise HTTPException(
            status_code=503,
            detail="PAD clinical model could not be loaded.",
        ) from exc


def _clean_category(value: str) -> str:
    value = value.strip()

    if not value or value.casefold() in {"unk", "unknown", "none"}:
        return "UNK"

    if value.casefold() == "true":
        return "True"

    if value.casefold() == "false":
        return "False"

    return value.upper()


@router.post("/api/v1/cancers/skin/clinical-analysis")
def pad_clinical_analysis(
    age: str | None = Form(default=None),
    sex: str = Form(...),
    region: str = Form(default="UNK"),
    itch: str = Form(default="UNK"),
    grew: str = Form(default="UNK"),
    hurt: str = Form(default="UNK"),
    changed: str = Form(default="UNK"),
    bleed: str = Form(default="UNK"),
    elevation: str = Form(default="UNK"),
):
    """Research-only PAD-UFES-20 clinical inference."""

    sex_value = sex.strip().casefold()

    if sex_value not in {"female", "male", "unknown"}:
        raise HTTPException(
            status_code=422,
            detail="Sex is required; select female, male, or not provided.",
        )

    age_value = None

    if age not in (None, ""):
        try:
            age_value = float(age)

            if not 0 <= age_value <= 120:
                raise ValueError

        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="Age must be a number between 0 and 120.",
            ) from exc

    symptoms = {
        "itch": itch,
        "grew": grew,
        "hurt": hurt,
        "changed": changed,
        "bleed": bleed,
        "elevation": elevation,
    }

    cleaned = {
        key: _clean_category(value)
        for key, value in symptoms.items()
    }

    for key, value in cleaned.items():
        if value not in {"True", "False", "UNK"}:
            raise HTTPException(
                status_code=422,
                detail=f"{key} must be True, False, or UNK.",
            )

    region_value = _clean_category(region)

    if region_value != "UNK" and region_value not in SUPPORTED_REGIONS:
        raise HTTPException(
            status_code=422,
            detail=(
                "region must be a supported PAD-UFES-20 body site or UNK."
            ),
        )


    patient = {
        "age": age_value,
        "sex": sex_value,
        "region": region_value,
        **cleaned,
    }

    try:
        model, preprocessor, labels = _load_pad_model()

        frame = pd.DataFrame(
            [{feature: patient[feature] for feature in FEATURES}],
            columns=FEATURES,
        )

        transformed = preprocessor.transform(frame)

        tensor = torch.as_tensor(
            transformed,
            dtype=torch.float32,
            device=config.DEVICE,
        )

        with torch.inference_mode():
            probabilities = torch.softmax(
                model(tensor), dim=1
            )[0].cpu().numpy()

        class_codes = [
            labels[str(i)] for i in range(len(labels))
        ]

        scores = {
            class_codes[i]: float(probabilities[i])
            for i in range(len(class_codes))
        }

        predicted_code = class_codes[int(probabilities.argmax())]

        result = {
            "analysisId": uuid.uuid4().hex,
            "cancerType": "skin",
            "moduleId": "pad-clinical-analysis",
            "dataset": "PAD-UFES-20",
            "prediction": predicted_code,
            "classification": predicted_code,
            "confidence": scores[predicted_code],
            "probabilities": scores,
            "patient": patient,



            "sexUsage": (
                "Recorded for the report only; not used by the "
                "existing PAD clinical model."
            ),

            "model": {
                "name": "PAD-UFES-20 Clinical Classifier",
                "architecture": "Clinical MLP (32 -> 128 -> 64 -> 32 -> 6)",
                "inputFeaturesAfterPreprocessing": len(
                    preprocessor.get_feature_names_out()
                ),
                "trainingStatus": "Trained",
            },

            "createdAt": datetime.now(timezone.utc).isoformat(),

            "disclaimer": (
                "Academic research prototype only. This output is not a "
                "medical diagnosis and must not replace examination by "
                "a qualified doctor. "
                "until checked by an authorized clinician."
            ),
        }

        # Persist the PAD clinical report using the existing API store.
        try:
            try:
                from . import api as api_module
            except ImportError:
                import api as api_module

            created_at = result["createdAt"]

            report = {
                "analysisId": result["analysisId"],
                "cancerType": "skin",
                "dataset": "PAD-UFES-20",
                "moduleId": "clinical-analysis",
                "moduleName": "Clinical Analysis",
                "uploadDate": created_at,
                "modelStatus": "connected",
                "analysisStatus": "completed",
                "fileName": "Not applicable — clinical-only analysis",
                "age": age_value,
                "sex": sex_value,
                "localization": region_value,
                "evaluationMetrics": None,
                "result": result,
            }

            api_module._save_report(report)
            api_module._reports[result["analysisId"]] = report

            result["reportStorage"] = "sqlite"

        except Exception:
            result["reportStorage"] = "memory-only"
            logger.exception(
                "Could not persist PAD clinical analysis report"
            )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("PAD clinical inference failed")

        raise HTTPException(
            status_code=503,
            detail="PAD clinical inference failed.",
        ) from exc


