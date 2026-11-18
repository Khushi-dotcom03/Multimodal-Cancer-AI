"""Multipart endpoint for the Brain image + clinical research workflow."""

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from Brain_cancer.clinical.service import BrainClinicalModelUnavailable
from Brain_cancer.image.service import BrainImageError, BrainModelUnavailable
from Brain_cancer.multimodal.service import service


router = APIRouter()


@router.post("/api/v1/cancers/brain/multimodal-analysis")
def brain_multimodal_analysis(
    file: UploadFile = File(..., description="JPG, JPEG, or PNG brain MRI image."),
    age: float = Form(..., ge=5, le=78, description="Age in years within the clinical model training range."),
    sex: Literal["M", "F"] = Form(..., description="Sex value represented in the clinical model training data."),
    site: str | None = Form(default=None, max_length=160, description="Optional cleaned anatomical location."),
):
    try:
        content = file.file.read(10 * 1024 * 1024 + 1)
    finally:
        file.file.close()

    try:
        return service.analyze(content, file.filename, file.content_type, age, sex, site)
    except BrainImageError as exc:
        message = str(exc)
        status = 413 if "10 MB" in message else 415 if "Unsupported" in message else 400
        raise HTTPException(status_code=status, detail=message) from exc
    except (BrainModelUnavailable, BrainClinicalModelUnavailable) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Combined brain research analysis failed. Please retry.") from exc
