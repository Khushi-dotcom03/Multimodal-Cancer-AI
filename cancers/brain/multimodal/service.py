"""Legacy parallel Brain outputs retained for the existing frontend contract.

The genuinely trained IDH fusion model is exposed separately by inference.py and
the /multimodal-idh-analysis endpoint; this compatibility service is not fusion.
"""

from __future__ import annotations

import uuid

from cancers.brain.clinical.service import (
    BrainClinicalModelUnavailable,
    service as brain_clinical_service,
)
from cancers.brain.image.service import (
    BrainImageError,
    BrainModelUnavailable,
    service as brain_image_service,
)


class BrainMultimodalService:
    def analyze(self, image_bytes: bytes, filename: str | None, content_type: str | None,
                age: float, sex: str, site: str | None) -> dict:
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
            "resultScope": {"kind": "parallel_model_outputs", "fused": False,
                "note": "Legacy independent model outputs; use the trained IDH fusion endpoint for learned fusion."},
        }


service = BrainMultimodalService()

__all__ = ["BrainClinicalModelUnavailable", "BrainImageError", "BrainModelUnavailable", "BrainMultimodalService", "service"]
