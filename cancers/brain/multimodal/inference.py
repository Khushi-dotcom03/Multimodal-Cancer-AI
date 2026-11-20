"""Load trained UTSW IDH models and infer from T1CE slices plus clinical fields."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from PIL import Image

from cancers.brain.multimodal.config import ARTIFACT_DIR, CLASSES, MAX_SLICES_PER_PATIENT, PRETRAINED_CHECKPOINT
from cancers.brain.multimodal.models import FusionModel, build_pretrained_effnet
from cancers.brain.multimodal.preprocessing import clinical_frame, select_slice_paths, MRI_IMAGE_TRANSFORM


class BrainIDHInference:
    def __init__(self, checkpoint_path: str | Path | None = None,
                 preprocessor_path: str | Path | None = None,
                 pretrained_image_checkpoint: str | Path | None = None,
                 device: str | None = None):
        self.checkpoint_path = Path(checkpoint_path or ARTIFACT_DIR / "brain_idh_fusion_best.pt")
        self.preprocessor_path = Path(preprocessor_path or ARTIFACT_DIR / "brain_idh_clinical_preprocessor.joblib")
        self.pretrained_image_checkpoint = Path(pretrained_image_checkpoint or PRETRAINED_CHECKPOINT)
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        if not self.checkpoint_path.is_file(): raise FileNotFoundError(f"Trained fusion checkpoint not found: {self.checkpoint_path}")
        if not self.preprocessor_path.is_file(): raise FileNotFoundError(f"Clinical preprocessor not found: {self.preprocessor_path}")
        self.checkpoint = torch.load(self.checkpoint_path, map_location=self.device, weights_only=True)
        self.model = FusionModel(self.checkpoint["clinical_dim"], self.checkpoint["mri_dim"])
        self.model.load_state_dict(self.checkpoint["state_dict"]); self.model.to(self.device).eval()
        self.preprocessor = joblib.load(self.preprocessor_path)
        self.encoder = build_pretrained_effnet(str(self.pretrained_image_checkpoint), self.device)

    def predict(self, slice_paths: list[str | Path], clinical: dict) -> dict:
        chosen = select_slice_paths([str(Path(p)) for p in slice_paths], MAX_SLICES_PER_PATIENT)
        images = []
        for path in chosen:
            try:
                with Image.open(path) as im: images.append(im.convert("L").copy())
            except Exception as exc:
                raise ValueError(f"Could not decode T1CE image {path}: {exc}") from exc
        return self.predict_images(images, clinical)

    def predict_images(self, images: list[Image.Image], clinical: dict) -> dict:
        if not images: raise ValueError("At least one T1CE slice is required")
        if len(images) > MAX_SLICES_PER_PATIENT:
            indices = np.linspace(0, len(images) - 1, MAX_SLICES_PER_PATIENT, dtype=int)
            images = [images[i] for i in indices]
        try:
            batch = torch.cat([MRI_IMAGE_TRANSFORM(image.convert("L").convert("RGB")).unsqueeze(0) for image in images]).to(self.device)
            with torch.inference_mode():
                embeddings = self.encoder(batch).cpu().numpy()
        except Exception as exc:
            raise ValueError(f"Could not preprocess T1CE slice: {exc}") from exc
        mri_features = np.mean(embeddings, axis=0, keepdims=True).astype(np.float32)
        clinical_input = pd.DataFrame([{
            "Age at Imaging": clinical.get("Age at Imaging", clinical.get("age")),
            "Tumor Grade": clinical.get("Tumor Grade", clinical.get("grade")),
            "Sex at birth": clinical.get("Sex at birth", clinical.get("sex")),
            "1p19Q CODEL": clinical.get("1p19Q CODEL", clinical.get("1p19q")),
            "MGMT": clinical.get("MGMT", clinical.get("mgmt")),
        }])
        transformed = self.preprocessor.transform(clinical_frame(clinical_input)).astype(np.float32)
        with torch.inference_mode():
            probabilities = torch.softmax(self.model(torch.from_numpy(mri_features).to(self.device), torch.from_numpy(transformed).to(self.device)), dim=1)[0].cpu().numpy()
        return {
            "task": "research prediction of IDH status",
            "predicted_class": CLASSES[int(probabilities.argmax())],
            "class_scores": {label: float(probabilities[i]) for i, label in enumerate(CLASSES)},
            "score_interpretation": "uncalibrated model scores; not a clinical diagnosis",
            "model": "Frozen EfficientNet-B0 T1CE embeddings + clinical MLP + learned feature-level fusion",
            "n_slices_used": int(embeddings.shape[0]),
            "checkpoint": str(self.checkpoint_path),
        }


def predict_patient(patient_id: str, data_root: str | Path, clinical: dict, **kwargs) -> dict:
    slice_dir = Path(data_root) / patient_id / "brain_t1ce"
    if not slice_dir.is_dir(): raise FileNotFoundError(f"T1CE folder not found for {patient_id}: {slice_dir}")
    paths = sorted(slice_dir.glob("*.png"))
    if not paths: raise FileNotFoundError(f"No T1CE PNG slices found for {patient_id}")
    return BrainIDHInference(**kwargs).predict(paths, clinical)
