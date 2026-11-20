from fastapi import APIRouter, HTTPException

from .registry import get_cancer, list_cancers

router = APIRouter(prefix="/api/v1/cancers", tags=["cancer-registry"])


@router.get("")
def cancers():
    return list_cancers()


@router.get("/{cancer_type}")
def cancer_details(cancer_type: str):
    config = get_cancer(cancer_type)
    if config is None:
        raise HTTPException(status_code=404, detail="Cancer type is not registered.")
    return config


@router.get("/{cancer_type}/clinical-schema")
def clinical_schema(cancer_type: str):
    config = get_cancer(cancer_type)
    if config is None:
        raise HTTPException(status_code=404, detail="Cancer type is not registered.")
    return {
        "cancerType": cancer_type,
        "status": config["status"],
        "features": config["clinicalFeatures"],
        "featureCountAfterPreprocessing": config["clinicalFeatureCountAfterPreprocessing"],
        "dataset": config.get("clinicalDataset", config["dataset"]),
        "message": "Only features used by the saved training pipeline are listed." if config["clinicalFeatures"] else "No compatible clinical model or feature schema is configured for this cancer type.",
    }
