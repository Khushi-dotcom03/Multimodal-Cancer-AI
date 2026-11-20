"""Brain MRI image-analysis API route backed by the original MIND model."""

from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile

from .service import BrainImageError, BrainModelUnavailable, service

router = APIRouter()


@router.post("/api/v1/analysis/brain-tumour")
def brain_image_analysis(file: UploadFile = File(...)):
    try:
        content = file.file.read(10 * 1024 * 1024 + 1)
    finally:
        file.file.close()
    try:
        image = service.decode_image(content, file.filename, file.content_type)
        result = service.analyze(image)
    except BrainImageError as exc:
        message = str(exc)
        status = 413 if "10 MB" in message else 415 if "Unsupported" in message else 400
        raise HTTPException(status_code=status, detail=message) from exc
    except BrainModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "analysisId": result["analysis_id"], "moduleId": "brain-tumour",
        "prediction": result["predicted_class"],
        "confidence": result["class_scores"][result["predicted_class"]],
        "classification": result["predicted_class"], "classScores": result["class_scores"],
        "heatmapUrl": result["gradcam"]["overlay"], "gradcam": result["gradcam"],
        "inferenceStatus": result["inference_status"], "disclaimer": result["disclaimer"],
        "model": {
            "name": result["model_name"], "architecture": result["model_architecture"],
            "dataset": "Brain Tumor MRI (MIND project)", "version": "Original best_model.pth",
            "trainingStatus": "Pretrained checkpoint",
            "evaluationStatus": "Research model; external validation not established",
            "lastUpdated": timestamp,
        },
        "createdAt": timestamp,
    }
