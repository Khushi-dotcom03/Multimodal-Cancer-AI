"""HTTP API for the WeCure skin lesion research frontend."""

import base64
import csv
import io
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

try:  # Support `uvicorn api:app` from Skin_cancer/backend/ and `uvicorn Skin_cancer.backend.api:app` at repo root.
    from . import config, fusion_utils as fu
    from .models.clinical_model import ClinicalMLP
    from .cancer_registry.registry import get_cancer
    from .cancer_registry.routes import router as cancer_registry_router
    from .pad_clinical_api import router as pad_clinical_router
    from .skin_ood_gate import score_skin_scope
except ImportError:  # pragma: no cover - used when backend/ is the import root
    import config
    import fusion_utils as fu
    from models.clinical_model import ClinicalMLP
    from cancer_registry.registry import get_cancer
    from cancer_registry.routes import router as cancer_registry_router
    from pad_clinical_api import router as pad_clinical_router
    from skin_ood_gate import score_skin_scope


MODEL_DIR = config.MODEL_DIR
RESULTS_DIR = config.RESULTS_DIR
DEVICE = config.DEVICE
MAX_IMAGE_BYTES = config.MAX_IMAGE_BYTES

app = FastAPI(
    title="WeCure Skin Cancer Research API",
    version="1.0.0",
    description="Research prototype for skin lesion image analysis. Not for clinical use.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(config.FRONTEND_ORIGINS),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(cancer_registry_router)
app.include_router(pad_clinical_router)

_models = None
_clinical_model = None
_reports: dict[str, dict] = {}
logger = logging.getLogger(__name__)


@app.post("/api/v1/cancers/skin/pad-multimodal-analysis")
async def pad_multimodal_analysis(
    file: UploadFile = File(...),
    age: str | None = Form(default=None),
    region: str = Form(default=""),
    itch: str = Form(default=""),
    grew: str = Form(default=""),
    hurt: str = Form(default=""),
    changed: str = Form(default=""),
    bleed: str = Form(default=""),
    elevation: str = Form(default=""),
    sex: str = Form(default="unknown"),
):
    """Run the trained same-dataset PAD-UFES-20 paired fusion model."""
    try:
        from .models.pad_fusion_model import PADFusionModel
        from .preprocessing.pad_clinical_preprocessing import CLINICAL_FEATURES
    except ImportError:
        from models.pad_fusion_model import PADFusionModel
        from preprocessing.pad_clinical_preprocessing import CLINICAL_FEATURES
    import pandas as pd
    import joblib
    import torch

    if age is None or not age.strip():
        raise HTTPException(status_code=422, detail="Age is required for PAD-UFES-20 Combined Analysis.")
    try:
        age_value = float(age)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Age must be a number between 0 and 120.") from exc
    if not 0 <= age_value <= 120:
        raise HTTPException(status_code=422, detail="Age must be between 0 and 120.")
    sex_value = sex.strip().casefold()
    if sex_value not in {"female", "male", "unknown"}:
        raise HTTPException(status_code=422, detail="Sex must be Female, Male, or Unknown.")
    supplied = {"region": region, "itch": itch, "grew": grew, "hurt": hurt, "changed": changed, "bleed": bleed, "elevation": elevation}
    if any(not value.strip() for value in supplied.values()):
        raise HTTPException(status_code=422, detail="All PAD clinical fields are required.")
    if region.strip().upper() not in {"ABDOMEN","ARM","BACK","CHEST","EAR","FACE","FOOT","FOREARM","HAND","LIP","NECK","NOSE","SCALP","THIGH","UNK"}:
        raise HTTPException(status_code=422, detail="Unsupported PAD lesion region.")
    if any(value.strip().casefold() not in {"true","false","unk"} for value in (itch,grew,hurt,changed,bleed,elevation)):
        raise HTTPException(status_code=422, detail="PAD symptom values must be True, False, or UNK.")
    content, image = await _read_validated_image(file)
    pad_dir = MODEL_DIR / "pad_ufes20"
    checkpoint_path = pad_dir / "pad_fusion_best.pth"
    preprocessor_path = pad_dir / "pad_fusion_preprocessor.joblib"
    if not checkpoint_path.is_file() or not preprocessor_path.is_file():
        raise HTTPException(status_code=503, detail="The evaluated PAD-UFES-20 image+clinical fusion model is not installed.")
    try:
        checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=True)
        preprocessor = joblib.load(preprocessor_path)
        if checkpoint.get("dataset") != "PAD-UFES-20" or checkpoint.get("classes") != ["ACK","BCC","MEL","NEV","SCC","SEK"]:
            raise ValueError("PAD fusion checkpoint metadata mismatch")
        model = PADFusionModel(int(checkpoint["input_features"]), 6).to(DEVICE)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        row = {"age": age_value, **supplied}
        clinical = preprocessor.transform(pd.DataFrame([row])[CLINICAL_FEATURES]).astype("float32")
        tensor = fu.EVAL_TF(image).unsqueeze(0).to(DEVICE)
        with torch.inference_mode():
            probabilities = torch.softmax(model(tensor, torch.as_tensor(clinical,device=DEVICE)), dim=1)[0].cpu().numpy()
    except Exception as exc:
        logger.exception("PAD fusion model inference failed")
        raise HTTPException(status_code=503, detail="The PAD-UFES-20 fusion model could not be loaded or run.") from exc
    classes = checkpoint["classes"]
    index = int(probabilities.argmax())
    scores = {classes[i]: float(probabilities[i]) for i in range(len(classes))}
    analysis_id = uuid.uuid4().hex
    created = datetime.now(timezone.utc).isoformat()
    image_url = f"data:{file.content_type};base64,{base64.b64encode(content).decode('ascii')}"
    patient = {"age": age_value, "sex": sex_value, "localization": region}
    class_names = {"ACK":"Actinic keratosis","BCC":"Basal cell carcinoma","MEL":"Melanoma","NEV":"Nevus","SCC":"Squamous cell carcinoma","SEK":"Seborrheic keratosis"}
    result = {
        "analysisId": analysis_id, "cancerType": "skin", "moduleId": "skin-cancer",
        "dataset": "PAD-UFES-20", "prediction": classes[index], "classification": classes[index], "classNames": class_names,
        "confidence": scores[classes[index]], "probabilities": scores, "patient": patient,
        "originalImageUrl": image_url,
        "model": {"name":"PAD-UFES-20 Image+Clinical Fusion Classifier","imageModel":"ResNet-18","clinicalModel":"PAD clinical feature encoder","fusion":"Feature-level multimodal fusion","architecture":"ResNet-18 image encoder + 8-field clinical MLP feature fusion","dataset":"PAD-UFES-20","version":"PAD fusion checkpoint","trainingStatus":"Trained","evaluationStatus":"Patient-disjoint holdout evaluated","lastUpdated":datetime.fromtimestamp(checkpoint_path.stat().st_mtime,timezone.utc).isoformat(),"bestEpoch":int(checkpoint["best_epoch"])},
        "createdAt": created,
        "disclaimer":"Academic research prototype only; this prediction is not a medical diagnosis.",
    }
    report = {"analysisId":analysis_id,"cancerType":"skin","moduleId":"skin-cancer","moduleName":"PAD-UFES-20 Combined Analysis","uploadDate":created,"modelStatus":"connected","analysisStatus":"completed","fileName":Path(file.filename or "uploaded-image").name,"age":age_value,"sex":sex_value,"sexUsage":"Recorded for report only; not used by the PAD-UFES-20 fusion model.","localization":region,"evaluationMetrics":None,"result":result}
    try:
        _save_report(report); result["reportStorage"]="sqlite"
    except (OSError, sqlite3.Error):
        result["reportStorage"]="memory-only"
    report["result"]=result; _reports[analysis_id]=report
    return result


async def _read_validated_image(upload: UploadFile) -> tuple[bytes, Image.Image]:
    """Validate upload type, actual format, dimensions and image integrity."""
    allowed_types = {"image/jpeg": "JPEG", "image/png": "PNG"}
    expected_format = allowed_types.get(upload.content_type)
    if expected_format is None:
        raise HTTPException(status_code=415, detail="Upload a JPEG or PNG image")

    content = await upload.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be between 1 byte and 10 MB")

    try:
        with Image.open(io.BytesIO(content)) as probe:
            if probe.format != expected_format:
                raise HTTPException(status_code=400, detail="File content does not match its declared image type")
            width, height = probe.size
            if width < 64 or height < 64:
                raise HTTPException(status_code=400, detail="Image dimensions must be at least 64 x 64 pixels")
            if width * height > 20_000_000:
                raise HTTPException(status_code=413, detail="Image dimensions exceed 20 megapixels")
            probe.verify()

        with Image.open(io.BytesIO(content)) as decoded:
            decoded.load()
            image = decoded.convert("RGB")

    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid or unreadable JPEG/PNG image") from exc

    return content, image


def _reports_connection():
    config.REPORTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(config.REPORTS_DB_PATH, timeout=10)
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS reports (analysis_id TEXT PRIMARY KEY, upload_date TEXT NOT NULL, payload TEXT NOT NULL)"
    )
    return connection


def _save_report(report: dict) -> None:
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    with _reports_connection() as connection:
        connection.execute(
            "INSERT INTO reports (analysis_id, upload_date, payload) VALUES (?, ?, ?) "
            "ON CONFLICT(analysis_id) DO UPDATE SET upload_date=excluded.upload_date, payload=excluded.payload",
            (report["analysisId"], report["uploadDate"], payload),
        )


def _get_report(analysis_id: str) -> dict | None:
    if analysis_id in _reports:
        return _reports[analysis_id]
    with _reports_connection() as connection:
        row = connection.execute(
            "SELECT payload FROM reports WHERE analysis_id = ?", (analysis_id,)
        ).fetchone()
    return json.loads(row[0]) if row else None


def _list_reports() -> list[dict]:
    with _reports_connection() as connection:
        rows = connection.execute(
            "SELECT analysis_id, payload FROM reports ORDER BY upload_date DESC"
        ).fetchall()
    reports = {analysis_id: json.loads(payload) for analysis_id, payload in rows}
    reports.update(_reports)
    return sorted(reports.values(), key=lambda report: report.get("uploadDate", ""), reverse=True)

EDUCATIONAL_OVERVIEWS = {
    "akiec": {
        "overview": "Actinic keratoses are sun-associated rough or scaly skin growths. Some can progress to squamous cell carcinoma, so a clinician should assess a suspected lesion.",
        "referenceTitle": "Actinic keratosis overview â€” American Academy of Dermatology",
        "source": "https://www.aad.org/public/diseases/skin-cancer/actinic-keratosis-overview",
    },
    "bcc": {
        "overview": "Basal cell carcinoma is a common skin-cancer category that can appear in several ways. A dermatologist can assess a spot and decide whether further examination is needed.",
        "referenceTitle": "Basal cell carcinoma â€” American Academy of Dermatology",
        "source": "https://www.aad.org/public/diseases/skin-cancer/basal-cell-carcinoma",
    },
    "bkl": {
        "overview": "Benign keratosis-like lesions include appearances that can resemble other skin growths. An AI category cannot establish whether a particular spot is benign.",
        "referenceTitle": "Seborrheic keratoses â€” American Academy of Dermatology",
        "source": "https://www.aad.org/public/diseases/a-z/seborrheic-keratoses-overview",
    },
    "df": {
        "overview": "Dermatofibroma is the name of a skin-lesion category in this dataset. This image model cannot confirm the identity of an individual lesion.",
        "referenceTitle": "Dermatofibroma â€” DermNet",
        "source": "https://dermnetnz.org/topics/benign-skin-lesions",
    },
    "mel": {
        "overview": "Melanoma is a skin-cancer category. A new or changing spot, or one that bleeds, itches, or becomes crusted, should be assessed promptly by a healthcare professional.",
        "referenceTitle": "Melanoma symptoms â€” NHS",
        "source": "https://www.nhs.uk/conditions/melanoma-skin-cancer/symptoms/",
    },
    "nv": {
        "overview": "Melanocytic nevi are commonly called moles. Many moles are harmless, but a new or changing mole should be checked by a healthcare professional.",
        "referenceTitle": "Moles â€” NHS",
        "source": "https://www.nhs.uk/conditions/moles/",
    },
    "vasc": {
        "overview": "Vascular lesion is a broad image-classification category. The model cannot confirm what a particular spot is; ask a dermatologist about a new, changing, or bleeding lesion.",
        "referenceTitle": "Vascular skin lesions â€” DermNet",
        "source": "https://dermnetnz.org/topics/vascular-proliferations-and-abnormalities-of-blood-vessels",
    },
}
HAM10000_REFERENCE = {
    "title": "The HAM10000 dataset (Tschandl et al., Scientific Data, 2018)",
    "url": "https://www.nature.com/articles/sdata2018161",
}


def models():
    global _models
    if _models is None:
        try:
            _models = fu.load_models(str(MODEL_DIR), DEVICE)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Model files could not be loaded") from exc
    return _models


def clinical_model():
    global _clinical_model
    if _clinical_model is None:
        try:
            import torch

            model = ClinicalMLP()
            state = torch.load(MODEL_DIR / "clinical_mlp_best.pth", map_location=DEVICE, weights_only=True)
            model.load_state_dict(state, strict=True)
            _clinical_model = model.to(DEVICE).eval()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Clinical model checkpoint could not be loaded") from exc
    return _clinical_model


def _validated_patient(age: str | None, sex: str, localization: str):
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
    return age_value


@app.post("/api/v1/clinical-analysis")
def clinical_analysis(
    age: str | None = Form(default=None),
    sex: str = Form(default="unknown"),
    localization: str = Form(default="unknown"),
):
    """Run the saved clinical MLP using the three fitted HAM10000 fields."""
    import torch

    age_value = _validated_patient(age, sex, localization)
    try:
        preprocessor = fu.joblib.load(MODEL_DIR / "clinical_preprocessor.joblib")
        features = fu.clinical_vector(preprocessor, age_value, sex, localization)
        with torch.inference_mode():
            tensor = torch.as_tensor(features, dtype=torch.float32, device=DEVICE)
            scores = torch.softmax(clinical_model()(tensor), dim=1)[0].cpu().numpy()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Clinical analysis failed")
        raise HTTPException(status_code=503, detail="Clinical model inference failed") from exc

    class_index = int(scores.argmax())
    class_code = fu.CLASSES[class_index]
    created_at = datetime.now(timezone.utc).isoformat()
    analysis_id = uuid.uuid4().hex
    checkpoint = MODEL_DIR / "clinical_mlp_best.pth"
    result = {
        "analysisId": analysis_id,
        "cancerType": "skin",
        "moduleId": "clinical-analysis",
        "prediction": fu.FULL_NAMES[class_code],
        "confidence": float(scores[class_index]),
        "classification": class_code,
        "classNames": fu.FULL_NAMES,
        "fileName": "Not applicable â€” clinical-only analysis",
        "patient": {"age": age_value, "sex": sex, "localization": localization},
        "probabilities": {fu.CLASSES[i]: float(scores[i]) for i in range(len(fu.CLASSES))},
        "model": {
            "name": "Clinical HAM10000 Classifier",
            "clinicalModel": "Clinical MLP",
            "architecture": "19-feature Clinical MLP (64 â†’ 32 â†’ 7)",
            "dataset": "HAM10000 metadata",
            "version": "Checkpoint file; release version not recorded",
            "trainingStatus": "Trained",
            "evaluationStatus": "Research evaluation complete",
            "lastUpdated": datetime.fromtimestamp(checkpoint.stat().st_mtime, timezone.utc).isoformat(),
        },
        "createdAt": created_at,
    }
    try:
        evaluation_metrics = get_metrics("clinical-analysis")
    except HTTPException:
        evaluation_metrics = None
    report = {
        "analysisId": analysis_id,
        "cancerType": "skin",
        "moduleId": "clinical-analysis",
        "moduleName": "Clinical Data Analysis",
        "uploadDate": created_at,
        "modelStatus": "connected",
        "analysisStatus": "completed",
        "fileName": result["fileName"],
        "age": age_value,
        "sex": sex,
        "localization": localization,
        "educationalOverview": EDUCATIONAL_OVERVIEWS.get(class_code),
        "researchReferences": [HAM10000_REFERENCE],
        "evaluationMetrics": evaluation_metrics,
        "result": result,
    }
    try:
        result["reportStorage"] = "sqlite"
        report["result"] = result
        _save_report(report)
        _reports[analysis_id] = report
    except (OSError, sqlite3.Error):
        result["reportStorage"] = "memory-only"
        report["result"] = result
        _reports[analysis_id] = report
        logger.exception("Could not persist clinical analysis report")
    return result


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
    content, pil_image = await _read_validated_image(image)

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


@app.post("/api/v1/image-analysis")
async def image_only_analysis(file: UploadFile = File(...)):
    """Image-only ResNet-18 analysis, separate from the multimodal fusion route."""
    import torch

    content, image = await _read_validated_image(file)

    resnet, backbone, _, _, cam = models()
    try:
        in_skin_scope, _ = score_skin_scope(image, backbone, MODEL_DIR, DEVICE)
    except Exception as exc:
        logger.exception("Skin OOD gate is unavailable")
        raise HTTPException(status_code=503, detail="Skin image scope validation is unavailable") from exc
    if not in_skin_scope:
        raise HTTPException(
            status_code=422,
            detail="The uploaded image was rejected by Skin Image Analysis scope validation. No HAM10000 class prediction or Grad-CAM was generated.",
        )
    tensor = fu.EVAL_TF(image).unsqueeze(0).to(DEVICE)
    with torch.enable_grad():
        logits = resnet(tensor)
        scores = torch.softmax(logits, 1)[0]
        class_index = int(scores.argmax())
        resnet.zero_grad()
        logits[0, class_index].backward()
    weights = cam.grads.mean(dim=(2, 3), keepdim=True)
    heat = torch.relu((weights * cam.acts).sum(1))[0].detach().cpu().numpy()
    heat = heat / (heat.max() + 1e-8)
    scores = scores.detach().cpu().numpy()
    class_code = fu.CLASSES[class_index]
    timestamp = datetime.now(timezone.utc).isoformat()
    analysis_id = uuid.uuid4().hex
    buffer = io.BytesIO()
    Image.fromarray(fu.overlay(image, heat)).save(buffer, format="JPEG", quality=85)
    heatmap_url = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    image_url = f"data:{file.content_type};base64,{base64.b64encode(content).decode('ascii')}"
    checkpoint = MODEL_DIR / "resnet18_best.pth"
    result = {
        "analysisId": analysis_id,
        "cancerType": "skin",
        "moduleId": "skin-image-analysis",
        "prediction": fu.FULL_NAMES[class_code],
        "confidence": float(scores[class_index]),
        "classification": class_code,
        "classNames": fu.FULL_NAMES,
        "fileName": Path(file.filename or "uploaded-image").name,
        "patient": {"age": None, "sex": "unknown", "localization": "unknown"},
        "probabilities": {fu.CLASSES[i]: float(scores[i]) for i in range(len(fu.CLASSES))},
        "originalImageUrl": image_url,
        "heatmapUrl": heatmap_url,
        "heatmapDescription": "Grad-CAM for the image-only ResNet-18 classifier. It highlights influential image regions and is not a lesion boundary or diagnosis.",
        "model": {
            "name": "Skin Lesion Image Classifier",
            "imageModel": "ResNet-18",
            "architecture": "ResNet-18 image classifier",
            "dataset": "HAM10000",
            "version": "Checkpoint file; release version not recorded",
            "trainingStatus": "Trained",
            "evaluationStatus": "Research evaluation complete",
            "lastUpdated": datetime.fromtimestamp(checkpoint.stat().st_mtime, timezone.utc).isoformat(),
        },
        "createdAt": timestamp,
    }
    try:
        metrics = get_metrics("skin-image-analysis")
    except HTTPException:
        metrics = None
    report = {
        "analysisId": analysis_id,
        "cancerType": "skin",
        "moduleId": "skin-image-analysis",
        "moduleName": "Skin Cancer Image Analysis",
        "uploadDate": timestamp,
        "modelStatus": "connected",
        "analysisStatus": "completed",
        "fileName": result["fileName"],
        "age": None,
        "sex": "unknown",
        "localization": "unknown",
        "educationalOverview": EDUCATIONAL_OVERVIEWS.get(class_code),
        "researchReferences": [HAM10000_REFERENCE],
        "evaluationMetrics": metrics,
        "result": result,
    }
    try:
        result["reportStorage"] = "sqlite"
        _save_report(report)
    except (OSError, sqlite3.Error):
        result["reportStorage"] = "memory-only"
        logger.exception("Could not persist image-only analysis report")
    _reports[analysis_id] = report
    return result


@app.post("/api/v1/analysis/{module_id}")
async def frontend_analysis(
    module_id: str,
    file: UploadFile = File(...),
    age: str | None = Form(default=None),
    sex: str = Form(default="unknown"),
    localization: str = Form(default="unknown"),
):
    """Match the multipart route and response shape used by the WeCure frontend."""
    if module_id != "skin-cancer":
        raise HTTPException(status_code=404, detail="This research module is not available")

    if age is None or not age.strip():
        raise HTTPException(status_code=422, detail="Age is required for Skin Combined Analysis.")
    if not sex or sex.strip().casefold() == "unknown":
        raise HTTPException(status_code=422, detail="Sex is required for Skin Combined Analysis; select male or female.")
    if not localization or localization.strip().casefold() == "unknown":
        raise HTTPException(status_code=422, detail="Lesion localization is required for Skin Combined Analysis.")

    age_value = _validated_patient(age, sex, localization)

    # Keep one request-local copy for the report; the server does not write images to disk.
    original_bytes = await file.read(MAX_IMAGE_BYTES + 1)
    await file.seek(0)
    result = await analyze(image=file, age=str(age_value), sex=sex, localization=localization)
    import torch
    preprocessor = fu.joblib.load(MODEL_DIR / "clinical_preprocessor.joblib")
    clinical_features = fu.clinical_vector(preprocessor, age_value, sex, localization)
    with torch.inference_mode():
        clinical_tensor = torch.as_tensor(clinical_features, dtype=torch.float32, device=DEVICE)
        clinical_probs_array = torch.softmax(clinical_model()(clinical_tensor), dim=1)[0].cpu().numpy()
    prediction = result["prediction"]
    timestamp = datetime.now(timezone.utc).isoformat()
    analysis_id = uuid.uuid4().hex
    original_image_url = (
        f"data:{file.content_type};base64,{base64.b64encode(original_bytes).decode('ascii')}"
        if original_bytes and len(original_bytes) <= MAX_IMAGE_BYTES
        else None
    )
    class_code = prediction["class"]
    response = {
        "analysisId": analysis_id,
        "cancerType": "skin",
        "moduleId": module_id,
        "prediction": prediction["label"],
        "confidence": prediction["confidence"],
        "classification": class_code,
        "fileName": Path(file.filename or "uploaded-image").name,
        "classNames": fu.FULL_NAMES,
        "patient": {
            "age": age_value,
            "sex": sex,
            "localization": localization,
        },
        "probabilities": result["probabilities"],
        "imageOnlyProbabilities": result["imageOnlyProbabilities"],
        "clinicalOnlyProbabilities": {fu.CLASSES[i]: float(clinical_probs_array[i]) for i in range(len(fu.CLASSES))},
        "originalImageUrl": original_image_url,
        "heatmapUrl": result["explanation"]["image"],
        "heatmapDescription": "Grad-CAM highlights image regions that influenced this model output. It is not a lesion boundary or a diagnosis.",
        "model": {
            "name": "Multimodal Skin Lesion Classifier",
            "imageModel": "ResNet-18",
            "clinicalModel": "Clinical MLP",
            "fusion": "Feature-level multimodal fusion",
            "architecture": "ResNet-18 with clinical MLP fusion",
            "dataset": "HAM10000",
            "version": "Checkpoint file; release version not recorded",
            "trainingStatus": "Trained",
            "evaluationStatus": "Research evaluation complete",
            "lastUpdated": get_model_info(module_id)["lastUpdated"],
        },
        "createdAt": timestamp,
    }
    try:
        evaluation_metrics = get_metrics(module_id)
    except HTTPException:
        evaluation_metrics = None

    # Store the actual response and image in memory for report viewing/download.
    # Nothing is written to disk; all entries disappear when this process exits.
    report = {
        "analysisId": analysis_id,
        "cancerType": "skin",
        "moduleId": module_id,
        "moduleName": "Combined Analysis",
        "uploadDate": timestamp,
        "modelStatus": "connected",
        "analysisStatus": "completed",
        "fileName": Path(file.filename or "uploaded-image").name,
        "age": age_value,
        "sex": sex,
        "localization": localization,
        "educationalOverview": EDUCATIONAL_OVERVIEWS.get(class_code),
        "researchReferences": [
            HAM10000_REFERENCE,
            *([{"title": EDUCATIONAL_OVERVIEWS[class_code]["referenceTitle"], "url": EDUCATIONAL_OVERVIEWS[class_code]["source"]}] if class_code in EDUCATIONAL_OVERVIEWS else []),
        ],
        "evaluationMetrics": evaluation_metrics,
        "result": response,
    }
    try:
        response["reportStorage"] = "sqlite"
        report["result"] = response
        _save_report(report)
        _reports[analysis_id] = report
    except (OSError, sqlite3.Error):
        response["reportStorage"] = "memory-only"
        report["result"] = response
        _reports[analysis_id] = report
        logger.exception("Could not persist analysis report; retaining it in process memory")
    return response


@app.get("/api/v1/modules/{module_id}/model")
def get_model_info(module_id: str):
    if module_id == "skin-image-analysis":
        checkpoint = MODEL_DIR / "resnet18_best.pth"
        if not checkpoint.is_file():
            raise HTTPException(status_code=503, detail="Image model checkpoint not found")
        return {
            "name": "Skin Lesion Image Classifier",
            "imageModel": "ResNet-18",
            "architecture": "ResNet-18 image classifier",
            "dataset": "HAM10000",
            "version": "Checkpoint file; release version not recorded",
            "trainingStatus": "Trained",
            "evaluationStatus": "Research evaluation complete",
            "lastUpdated": datetime.fromtimestamp(checkpoint.stat().st_mtime, timezone.utc).isoformat(),
        }
    if module_id == "clinical-analysis":
        checkpoint = MODEL_DIR / "clinical_mlp_best.pth"
        if not checkpoint.is_file():
            raise HTTPException(status_code=503, detail="Clinical model checkpoint not found")
        return {
            "name": "Clinical HAM10000 Classifier",
            "clinicalModel": "Clinical MLP",
            "architecture": "19-feature Clinical MLP (64 â†’ 32 â†’ 7)",
            "dataset": "HAM10000 metadata",
            "version": "Checkpoint file; release version not recorded",
            "trainingStatus": "Trained",
            "evaluationStatus": "Research evaluation complete",
            "lastUpdated": datetime.fromtimestamp(checkpoint.stat().st_mtime, timezone.utc).isoformat(),
        }
    if module_id != "skin-cancer":
        raise HTTPException(status_code=404, detail="Research module not available")

    weight_files = [MODEL_DIR / "resnet18_best.pth", MODEL_DIR / "fusion_best.pth"]
    last_updated = max(path.stat().st_mtime for path in weight_files if path.is_file())
    return {
        "name": "Multimodal Skin Lesion Classifier",
        "imageModel": "ResNet-18",
        "clinicalModel": "Clinical MLP",
        "fusion": "Feature-level multimodal fusion",
        "architecture": "ResNet-18 with clinical MLP fusion",
        "dataset": "HAM10000",
        "version": "Checkpoint file; release version not recorded",
        "trainingStatus": "Trained",
        "evaluationStatus": "Research evaluation complete",
        "lastUpdated": datetime.fromtimestamp(last_updated, timezone.utc).isoformat()
    }


@app.get("/api/v1/modules/{module_id}/metrics")
def get_metrics(module_id: str):
    if module_id not in {"skin-cancer", "skin-image-analysis", "clinical-analysis"}:
        raise HTTPException(status_code=404, detail="Research module not available")

    prefix = {"skin-cancer": "fusion", "skin-image-analysis": "image_only", "clinical-analysis": "clinical_only"}[module_id]
    metrics_file = RESULTS_DIR / f"{prefix}_metrics.json"
    predictions_file = RESULTS_DIR / f"{prefix}_test_preds.csv"

    if not metrics_file.exists() or not predictions_file.exists():
        raise HTTPException(status_code=503, detail="Evaluation files not found")

    try:
        with metrics_file.open("r", encoding="utf-8") as f:
            metrics = json.load(f)

        labels = list(fu.CLASSES)
        matrix = [[0 for _ in labels] for _ in labels]
        label_to_index = {label: i for i, label in enumerate(labels)}

        def class_index(value: str) -> int | None:
            # The saved evaluation CSV uses integer class IDs in CLASSES order.
            if value in label_to_index:
                return label_to_index[value]
            try:
                index = int(value)
            except (TypeError, ValueError):
                return None
            return index if 0 <= index < len(labels) else None

        with predictions_file.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                actual = class_index(row["true"])
                predicted = class_index(row["pred"])
                if actual is None or predicted is None:
                    raise ValueError("Unexpected class label in evaluation predictions")
                matrix[actual][predicted] += 1

        weighted = metrics["weighted avg"]

        return {
            "accuracy": float(metrics["accuracy"]),
            "precision": float(weighted["precision"]),
            "recall": float(weighted["recall"]),
            "f1": float(weighted["f1-score"]),
            "macroF1": float(metrics["macro avg"]["f1-score"]),
            "testSamples": int(metrics["weighted avg"]["support"]),
            "confusionMatrix": {
                "labels": labels,
                "matrix": matrix
            }
        }

    except (OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        raise HTTPException(status_code=503, detail="Could not read evaluation metrics") from exc


def _require_cancer_model(cancer_type: str, task: str) -> dict:
    cancer = get_cancer(cancer_type)
    if cancer is None:
        raise HTTPException(status_code=404, detail="Cancer type is not registered.")
    model_file = (cancer.get("modelIds") or {}).get(task)
    if cancer.get("status") != "available" or not model_file:
        raise HTTPException(
            status_code=503,
            detail=f"No validated {task} model is configured for {cancer['displayName']}. No other cancer model will be used.",
        )
    if not (MODEL_DIR / model_file).is_file():
        raise HTTPException(status_code=503, detail=f"The configured {task} checkpoint is missing.")
    return cancer


@app.post("/api/v1/cancers/{cancer_type}/clinical-analysis")
def cancer_clinical_analysis(
    cancer_type: str,
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
    cancer = _require_cancer_model(cancer_type, "clinical")
    if cancer_type != "skin" or cancer.get("clinicalDataset") != "PAD-UFES-20":
        raise HTTPException(status_code=503, detail=f"Clinical inference is not configured for {cancer['displayName']}.")
    try:
        from .pad_clinical_api import pad_clinical_analysis
    except ImportError:
        from pad_clinical_api import pad_clinical_analysis
    return pad_clinical_analysis(age, sex, region, itch, grew, hurt, changed, bleed, elevation)


@app.post("/api/v1/cancers/{cancer_type}/image-analysis")
async def cancer_image_analysis(cancer_type: str, file: UploadFile = File(...)):
    cancer = _require_cancer_model(cancer_type, "image")
    if cancer_type != "skin" or cancer.get("imageDataset") != "HAM10000":
        raise HTTPException(status_code=503, detail=f"Image inference is not configured for {cancer['displayName']}.")
    return await image_only_analysis(file)


@app.post("/api/v1/cancers/{cancer_type}/multimodal-analysis")
async def cancer_multimodal_analysis(
    cancer_type: str,
    file: UploadFile = File(...),
    age: str | None = Form(default=None),
    sex: str = Form(default="unknown"),
    localization: str = Form(default="unknown"),
):
    cancer = _require_cancer_model(cancer_type, "fusion")
    required_ham_artifacts = (cancer.get("fusionClinicalPreprocessor"), cancer.get("fusionClinicalModel"))
    if cancer_type != "skin" or cancer.get("imageDataset") != cancer.get("fusionDataset") or not all(required_ham_artifacts):
        raise HTTPException(status_code=503, detail=f"A compatible same-dataset fusion pipeline is not configured for {cancer['displayName']}.")
    if any(not (MODEL_DIR / artifact).is_file() for artifact in required_ham_artifacts):
        raise HTTPException(status_code=503, detail="A configured clinical feature artifact for Combined Analysis is missing.")
    if int(cancer.get("fusionClinicalFeatureCountAfterPreprocessing", 0)) != 19:
        raise HTTPException(status_code=503, detail="The configured HAM fusion feature schema does not match its checkpoint.")
    return await frontend_analysis("skin-cancer", file, age, sex, localization)


@app.get("/api/v1/reports")
def list_reports():
    """Return actual reports persisted by this API and those held in the current process."""
    return [
        {key: value for key, value in report.items() if key != "result"}
        for report in _list_reports()
    ]


def _report_pdf(report: dict) -> bytes:
    """Build a PDF only from fields actually stored for this analysis."""
    import html

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image as PDFImage
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    def p(value, style="BodyText"):
        return Paragraph(html.escape(str(value)), styles[style])

    def data_image(value):
        if not isinstance(value, str) or not value.startswith("data:image/") or "," not in value:
            return None
        try:
            payload = base64.b64decode(value.split(",", 1)[1], validate=True)
            image = PDFImage(io.BytesIO(payload), width=2.45 * inch, height=2.45 * inch, kind="proportional")
            return image
        except (ValueError, OSError):
            return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=48, bottomMargin=44,
        title=f"WeCure research report {report.get('analysisId', '')}",
        author="WeCure research platform",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="WCTitle", parent=styles["Title"], fontSize=18, leading=23, textColor=colors.HexColor("#0F766E"), alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="WCSection", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#123047"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="WCFootnote", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#526273")))
    styles.add(ParagraphStyle(name="WCDisclaimer", parent=styles["BodyText"], fontSize=9, leading=13, textColor=colors.HexColor("#7C2D12"), backColor=colors.HexColor("#FFF7ED"), borderColor=colors.HexColor("#FED7AA"), borderWidth=0.5, borderPadding=8, spaceBefore=8))

    story = [p("WeCure â€” Research Analysis Report", "WCTitle"), p("Educational research output â€¢ Not a medical diagnosis", "WCFootnote"), Spacer(1, 10)]
    result = report.get("result") if isinstance(report.get("result"), dict) else {}
    code = result.get("classification")
    label = result.get("prediction")
    if isinstance(label, dict):
        code = code or label.get("class")
        label = label.get("label")
    if not label and code in fu.FULL_NAMES:
        label = fu.FULL_NAMES[code]
    if code and isinstance(result.get("classNames"), dict):
        label = result["classNames"].get(code, label or code)

    story.append(p("Patient and image information", "WCSection"))
    patient_rows = [
        [p("Analysis ID"), p(report.get("analysisId") or "Not available")],
        [p("Module"), p(report.get("moduleName") or report.get("moduleId") or "Not available")],
        [p("Age"), p(f"{report['age']:g}" if isinstance(report.get("age"), (int, float)) else "Not provided")],
        [p("Sex"), p("Not provided" if report.get("sex") in (None, "unknown") else report["sex"])],
        [p("Lesion location"), p("Not provided" if report.get("localization") in (None, "unknown") else report["localization"])],
        [p("Uploaded filename"), p(report.get("fileName") or "Not provided")],
        [p("Uploaded at (UTC)"), p(report.get("uploadDate") or result.get("createdAt") or "Not available")],
    ]
    info = Table(patient_rows, colWidths=[1.55 * inch, 4.95 * inch], hAlign="LEFT")
    info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E1EA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info)

    story.append(p("AI prediction", "WCSection"))
    if label or code:
        prediction_rows = [
            [p("Predicted class"), p(label or "Not available")],
            [p("Class code"), p(code or "Not available")],
            [p("Model confidence"), p(f"{float(result['confidence']) * 100:.2f}%" if isinstance(result.get("confidence"), (int, float)) else "Not available")],
        ]
        story.append(Table(prediction_rows, colWidths=[1.55 * inch, 4.95 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E1EA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])))
    else:
        story.append(p("Prediction details were not stored for this report."))

    probabilities = result.get("probabilities")
    available_probs = [(c, probabilities[c]) for c in fu.CLASSES if isinstance(probabilities, dict) and isinstance(probabilities.get(c), (int, float))]
    if available_probs:
        story.append(Spacer(1, 5))
        prob_rows = [[p("Class"), p("Dataset label"), p("Probability")]]
        class_names = result.get("classNames") if isinstance(result.get("classNames"), dict) else {}
        prob_rows.extend([[p(c), p(class_names.get(c) or fu.FULL_NAMES.get(c, c)), p(f"{float(v) * 100:.2f}%")] for c, v in available_probs])
        prob_table = Table(prob_rows, colWidths=[0.85 * inch, 4.15 * inch, 1.5 * inch], repeatRows=1)
        prob_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2F4F1")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E1EA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([p("Fusion model class probabilities", "Heading3"), prob_table])
    else:
        story.append(p("Class probabilities were not stored for this older analysis."))

    story.append(p("Visual explainability", "WCSection"))
    original = data_image(result.get("originalImageUrl"))
    heatmap = data_image(result.get("heatmapUrl"))
    visuals = [[original or p("Original image was not retained for this report."), heatmap or p("Grad-CAM image is not available for this report.")]]
    visual_table = Table(visuals, colWidths=[3.25 * inch, 3.25 * inch], hAlign="LEFT")
    visual_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([visual_table, Spacer(1, 4), p("Left: uploaded image. Right: Grad-CAM overlay. Grad-CAM indicates image regions that influenced this model output; it is not a lesion segmentation, proof, or diagnosis.", "WCFootnote")])

    model = result.get("model") if isinstance(result.get("model"), dict) else {}
    story.append(p("Model information and evaluation", "WCSection"))
    model_rows = [
        [p("Image model"), p(model.get("imageModel") or "Not recorded")],
        [p("Clinical model"), p(model.get("clinicalModel") or "Not recorded")],
        [p("Checkpoint version"), p(model.get("version") or "Not recorded")],
        [p("Fusion architecture"), p(model.get("architecture") or "Multimodal image + clinical feature fusion")],
        [p("Dataset"), p(model.get("dataset") or "HAM10000")],
    ]
    story.append(Table(model_rows, colWidths=[1.55 * inch, 4.95 * inch], style=TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E1EA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])))
    evaluation = report.get("evaluationMetrics")
    if not isinstance(evaluation, dict):
        try:
            evaluation = get_metrics("skin-cancer")
        except HTTPException:
            evaluation = None
    if isinstance(evaluation, dict):
        eval_rows = [[p("Metric"), p("Saved test evaluation")]]
        for key, title in [("accuracy", "Accuracy"), ("precision", "Weighted precision"), ("recall", "Weighted recall"), ("f1", "Weighted F1-score"), ("macroF1", "Macro F1-score")]:
            if isinstance(evaluation.get(key), (int, float)):
                eval_rows.append([p(title), p(f"{float(evaluation[key]) * 100:.2f}%")])
        if isinstance(evaluation.get("testSamples"), int):
            eval_rows.append([p("Test samples"), p(evaluation["testSamples"])])
        story.extend([Spacer(1, 5), Table(eval_rows, colWidths=[3.25 * inch, 3.25 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2F4F1")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E1EA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))])
    else:
        story.append(p("Evaluation metrics are unavailable for this report."))

    story.append(p("Educational information", "WCSection"))
    education = report.get("educationalOverview")
    if not isinstance(education, dict) and code:
        education = EDUCATIONAL_OVERVIEWS.get(code)
    if isinstance(education, dict):
        story.append(p(education.get("overview", "Educational overview unavailable.")))
        source = education.get("source")
        if source:
            safe_url = html.escape(str(source), quote=True)
            story.append(Paragraph(f'<link href="{safe_url}" color="#0F766E">Educational reference</link>', styles["WCFootnote"]))
    else:
        story.append(p("No category-specific educational information was stored with this report."))
    story.append(Paragraph(
        "This experimental AI output is not a confirmed diagnosis and must not be used to choose treatment. A qualified dermatologist must assess skin concerns; changing, bleeding, itchy, crusted, or non-healing spots should be discussed with a healthcare professional.",
        styles["WCDisclaimer"],
    ))
    references = report.get("researchReferences") or [HAM10000_REFERENCE]
    story.append(p("Research references", "WCSection"))
    for reference in references:
        if isinstance(reference, dict) and reference.get("url"):
            title = html.escape(str(reference.get("title") or reference["url"]))
            url = html.escape(str(reference["url"]), quote=True)
            story.append(Paragraph(f'<link href="{url}" color="#0F766E">{title}</link>', styles["WCFootnote"]))
    story.append(Spacer(1, 7))
    storage_note = (
        "This detailed report is stored in the configured SQLite database, including image data and clinical details."
        if result.get("reportStorage") == "sqlite"
        else "This report is held in API memory only and may be lost when the API process exits."
    )
    story.append(p(storage_note + " Older records created before persistence may remain only in the process that originally created them.", "WCFootnote"))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(42, 25, "WeCure research prototype â€¢ Not for clinical diagnosis")
        canvas.drawRightString(A4[0] - 42, 25, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


@app.get("/api/v1/reports/{analysis_id}/download")
def download_report(analysis_id: str):
    report = _get_report(analysis_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found in this API session")
    try:
        pdf = _report_pdf(report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not generate the research report PDF") from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="wecure-report-{analysis_id}.pdf"'},
    )


@app.get("/api/v1/reports/{analysis_id}")
def get_report(analysis_id: str):
    report = _get_report(analysis_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found in this API session")
    return report



