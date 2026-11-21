"""Common FastAPI application for the four existing cancer modules."""

from cancer_modules.brain_cancer.clinical.api import router as brain_clinical_router
from cancer_modules.brain_cancer.image.api import router as brain_image_router
from cancer_modules.brain_cancer.multimodal.api import router as brain_multimodal_router
from cancer_modules.breast_cancer.module1_image_analysis.api import router as breast_image_router
from cancer_modules.breast_cancer.module2_clinical_analysis.api import router as breast_clinical_router
from cancer_modules.breast_cancer.module3_multimodal_fusion.api import router as breast_fusion_router
from cancer_modules.lung_cancer.api import router as lung_router
from cancer_modules.skin_cancer.backend.api import app

app.title = "Multimodal Cancer Research API"
app.description = "Shared research API for the existing skin, lung and brain model implementations."
app.include_router(lung_router)
app.include_router(brain_image_router)
app.include_router(brain_clinical_router)
app.include_router(brain_multimodal_router)
app.include_router(breast_image_router)
app.include_router(breast_clinical_router)
app.include_router(breast_fusion_router)
