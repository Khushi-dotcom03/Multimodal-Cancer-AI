"""FastAPI endpoint for Brain Clinical subtype analysis."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cancers.brain.clinical.service import BrainClinicalModelUnavailable, service


router = APIRouter()


class BrainClinicalRequest(BaseModel):
    age: float = Field(ge=5, le=78, description="Age in years; validated to the observed IPD-Brain range.")
    sex: Literal["M", "F"]
    site: str | None = Field(default=None, max_length=160, description="Optional anatomical site text.")


@router.post("/api/v1/cancers/brain/clinical-analysis")
def brain_clinical_analysis(payload: BrainClinicalRequest):
    try:
        return service.analyze(payload.age, payload.sex, payload.site)
    except BrainClinicalModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
