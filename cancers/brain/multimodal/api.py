"""Multipart endpoint for the Brain image + clinical research workflow."""

from io import BytesIO
from threading import Lock
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from cancers.brain.clinical.service import BrainClinicalModelUnavailable
from cancers.brain.image.service import BrainImageError, BrainModelUnavailable
from cancers.brain.multimodal.service import service
from cancers.brain.multimodal.inference import BrainIDHInference
from cancers.brain.multimodal.config import ARTIFACT_DIR


router = APIRouter()
_idh_service = None
_idh_service_lock = Lock()


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


@router.post("/api/v1/cancers/brain/multimodal-idh-analysis")
async def brain_multimodal_idh_analysis(
    files: list[UploadFile] = File(..., description="One or more PNG/JPG T1CE MRI slices from the same patient."),
    age_at_imaging: float | None = Form(default=None, ge=0, le=120),
    sex_at_birth: str | None = Form(default=None),
    tumor_grade: float | None = Form(default=None, ge=1, le=4),
    codeletion_1p19q: str | None = Form(default=None),
    mgmt: str | None = Form(default=None),
):
    """Run the saved, jointly trained IDH fusion model on a single patient's inputs."""
    global _idh_service
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one T1CE slice.")
    if len(files) > 48:
        raise HTTPException(status_code=400, detail="Upload at most 48 T1CE slices for one patient.")
    images = []
    total_bytes = 0
    try:
        for upload in files:
            content = await upload.read(15 * 1024 * 1024 + 1)
            total_bytes += len(content)
            if total_bytes > 100 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Combined MRI slice uploads must be 100 MB or smaller.")
            if len(content) > 15 * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"{upload.filename or 'A slice'} exceeds 15 MB.")
            try:
                with Image.open(BytesIO(content)) as image:
                    if image.format not in {"PNG", "JPEG"}:
                        raise HTTPException(status_code=415, detail="T1CE slices must be PNG or JPEG images.")
                    image.verify()
                with Image.open(BytesIO(content)) as image:
                    images.append(image.convert("L").copy())
            except HTTPException:
                raise
            except (UnidentifiedImageError, OSError) as exc:
                raise HTTPException(status_code=400, detail=f"Could not decode {upload.filename or 'uploaded image'}.") from exc
        with _idh_service_lock:
            if _idh_service is None:
                checkpoint = ARTIFACT_DIR / "brain_idh_fusion_best.pt"
                if not checkpoint.is_file():
                    raise HTTPException(status_code=503, detail="Trained IDH fusion checkpoint is unavailable. Run the multimodal training pipeline first.")
                _idh_service = BrainIDHInference()
        return _idh_service.predict_images(images, {
            "Age at Imaging": age_at_imaging,
            "Sex at birth": sex_at_birth,
            "Tumor Grade": tumor_grade,
            "1p19Q CODEL": codeletion_1p19q,
            "MGMT": mgmt,
        })
    except HTTPException:
        raise
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"IDH fusion inference failed: {exc}") from exc
    finally:
        for upload in files:
            await upload.close()
