"""Configuration for the patient-level UTSW MRI + clinical experiment."""

from pathlib import Path
import os

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[2]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "brain cancer" / "archive (2)" / "UTSW_Glioma_2D" / "dataset"
DEFAULT_CLINICAL_FILE = PROJECT_ROOT / "data" / "brain cancer" / "UTSW_Glioma_Metadata-2-1.tsv"
DEFAULT_PRETRAINED_CHECKPOINT = PROJECT_ROOT / "weights" / "best_model.pth"
ARTIFACT_DIR = MODULE_DIR / "artifacts"
REPORT_DIR = MODULE_DIR / "reports"

DATA_ROOT = Path(os.getenv("BRAIN_MM_DATA_ROOT", DEFAULT_DATA_ROOT))
CLINICAL_FILE = Path(os.getenv("BRAIN_MM_CLINICAL_FILE", DEFAULT_CLINICAL_FILE))
PRETRAINED_CHECKPOINT = Path(os.getenv("BRAIN_MM_PRETRAINED_CHECKPOINT", DEFAULT_PRETRAINED_CHECKPOINT))
SEED = int(os.getenv("BRAIN_MM_SEED", "42"))
MAX_SLICES_PER_PATIENT = int(os.getenv("BRAIN_MM_SLICES_PER_PATIENT", "8"))
BATCH_SIZE = int(os.getenv("BRAIN_MM_BATCH_SIZE", "32"))
EPOCHS = int(os.getenv("BRAIN_MM_EPOCHS", "60"))
PATIENCE = int(os.getenv("BRAIN_MM_PATIENCE", "10"))
IMAGE_SIZE = 224
CLASSES = ["wild type", "mutated"]
CLINICAL_NUMERIC = ["Age at Imaging", "Tumor Grade"]
CLINICAL_CATEGORICAL = ["Sex at birth", "1p19Q CODEL", "MGMT"]
