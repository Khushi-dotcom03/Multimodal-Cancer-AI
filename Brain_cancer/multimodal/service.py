"""Compose existing brain image and clinical inference without score fusion."""

from __future__ import annotations

import uuid

from Brain_cancer.clinical.service import (
    BrainClinicalModelUnavailable,
    service as brain_clinical_service,
)
from Brain_cancer.image.service import (
    BrainImageError,
    BrainModelUnavailable,
    service as brain_image_service,
)


class BrainMultimodalService:
    """Run both pretrained models and return their separate, real outputs.

    The models have incompatible target spaces and were not jointly trained on
    paired examples, so this service deliberately does not blend their scores.
    """

    def analyze(
        self,
        image_bytes: bytes,
        filename: str | None,
        content_type: str | None,
        age: float,
        sex: str,
        site: str | None,
    ) -> dict:
        image = brain_image_service.decode_image(image_bytes, filename, content_type)
        image_result = brain_image_service.analyze(image)
        clinical_result = brain_clinical_service.analyze(age, sex, site)

        return {
            "analysisId": uuid.uuid4().hex,
            "imageResult": {
                "analysisId": image_result["analysis_id"],
                "predictedClass": image_result["predicted_class"],
                "classScores": image_result["class_scores"],
                "modelName": image_result["model_name"],
                "architecture": image_result["model_architecture"],
                "gradcam": image_result["gradcam"],
                "disclaimer": image_result["disclaimer"],
            },
            "clinicalResult": clinical_result,
            "resultScope": {
                "kind": "parallel_model_outputs",
                "fused": False,
                "note": (
                    "The image model classifies Glioma, Meningioma, No Tumor, or Pituitary Tumor. "
                    "The separate clinical model estimates glioma subtype among the represented "
                    "IPD-Brain glioma cohort. No brain-specific joint fusion checkpoint or paired "
                    "training set is available, so these independent scores are not mathematically fused."
                ),
            },
        }


service = BrainMultimodalService()

__all__ = [
    "BrainClinicalModelUnavailable",
    "BrainImageError",
    "BrainModelUnavailable",
    "BrainMultimodalService",
    "service",
]
