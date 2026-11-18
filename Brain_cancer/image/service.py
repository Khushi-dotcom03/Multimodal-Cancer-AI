"""MIND brain MRI inference, using the selected project's original model contract."""

from __future__ import annotations

import base64
import io
import os
import uuid
from pathlib import Path
from threading import Lock

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError
from torchvision import models, transforms


CLASS_NAMES = ["Glioma", "Meningioma", "No Tumor", "Pituitary Tumor"]
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
DISCLAIMER = (
    "This is an AI-based research and educational classification result. It is not a medical diagnosis "
    "and must not replace professional radiological evaluation."
)
MODEL_NAME = "MIND Brain MRI Classifier"
MODEL_ARCHITECTURE = "EfficientNet-B0"

PREPROCESS = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


class BrainImageError(ValueError):
    """A client-correctable image upload error."""


class BrainModelUnavailable(RuntimeError):
    """The original checkpoint is missing or incompatible."""


class BrainMRIService:
    def __init__(self, checkpoint_path: str | Path | None = None, device: str | None = None):
        self.checkpoint_path = Path(
            checkpoint_path
            or os.getenv("BRAIN_MRI_CHECKPOINT", Path(__file__).resolve().parents[1] / "weights" / "best_model.pth")
        )
        requested = device or os.getenv("BRAIN_MRI_DEVICE", "auto")
        self.device = torch.device("cuda" if requested == "auto" and torch.cuda.is_available() else "cpu" if requested == "auto" else requested)
        self._model: nn.Module | None = None
        self._load_lock = Lock()

    def load_model(self) -> nn.Module:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            if not self.checkpoint_path.is_file():
                raise BrainModelUnavailable(f"Original MIND checkpoint not found: {self.checkpoint_path}")
            try:
                # weights=None avoids an unrelated ImageNet download; the original checkpoint
                # supplies every parameter and is loaded strictly below.
                model = models.efficientnet_b0(weights=None)
                model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(CLASS_NAMES))
                state = torch.load(self.checkpoint_path, map_location=self.device, weights_only=True)
                model.load_state_dict(state, strict=True)
                model.to(self.device).eval()
                self._model = model
            except Exception as exc:
                raise BrainModelUnavailable(f"Could not load original MIND checkpoint at {self.checkpoint_path}: {exc}") from exc
        return self._model

    @staticmethod
    def decode_image(content: bytes, filename: str | None, content_type: str | None) -> Image.Image:
        allowed = {".jpg", ".jpeg", ".png"}
        suffix = Path(filename or "").suffix.lower()
        if suffix not in allowed or content_type not in {
            None, "", "application/octet-stream", "image/jpeg", "image/jpg", "image/pjpeg", "image/png"
        }:
            raise BrainImageError("Unsupported file format. Upload a JPG, JPEG, or PNG image.")
        if not content:
            raise BrainImageError("The uploaded file is empty.")
        if len(content) > MAX_IMAGE_BYTES:
            raise BrainImageError("Image must be 10 MB or smaller.")
        try:
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise BrainImageError("Unsupported image encoding. Upload a JPG or PNG image.")
                width, height = image.size
                if width < 32 or height < 32:
                    raise BrainImageError("Image dimensions must be at least 32 × 32 pixels.")
                if width * height > MAX_IMAGE_PIXELS:
                    raise BrainImageError("Image dimensions are too large to process safely.")
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                return image.convert("RGB")
        except BrainImageError:
            raise
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise BrainImageError("The uploaded file is not a valid, readable image.") from exc

    @staticmethod
    def _png_data_url(image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    def analyze(self, image: Image.Image) -> dict:
        model = self.load_model()
        activation: torch.Tensor | None = None

        def capture(_module, _inputs, output):
            nonlocal activation
            activation = output
            if output.requires_grad:
                output.retain_grad()

        # EfficientNet-B0's last feature block is the spatial feature map used for Grad-CAM.
        handle = model.features[-1].register_forward_hook(capture)
        try:
            tensor = PREPROCESS(image.convert("RGB")).unsqueeze(0).to(self.device)
            model.zero_grad(set_to_none=True)
            logits = model(tensor)
            probabilities = F.softmax(logits, dim=1)[0]
            predicted_index = int(probabilities.argmax().item())
            cam_available = False
            gradcam_url = overlay_url = None
            try:
                if activation is None:
                    raise RuntimeError("Target feature layer did not produce activations")
                model.zero_grad(set_to_none=True)
                logits[0, predicted_index].backward()
                gradients = activation.grad
                if gradients is None:
                    raise RuntimeError("Gradients were not captured")
                weights = gradients.mean(dim=(2, 3), keepdim=True)
                cam = torch.relu((weights * activation).sum(dim=1, keepdim=True))
                cam = F.interpolate(cam, size=(image.height, image.width), mode="bilinear", align_corners=False)[0, 0]
                cam = cam.detach().cpu().numpy()
                maximum = float(cam.max())
                if not np.isfinite(cam).all() or maximum <= 0:
                    raise RuntimeError("Grad-CAM activation was empty")
                cam = np.clip(cam / maximum, 0, 1)
                heat = np.zeros((*cam.shape, 4), dtype=np.uint8)
                # A simple blue-to-red map, with alpha tied to activation (transparent background).
                heat[..., 0] = (255 * cam).astype(np.uint8)
                heat[..., 1] = (80 * (1 - cam)).astype(np.uint8)
                heat[..., 2] = (255 * (1 - cam)).astype(np.uint8)
                heat[..., 3] = (170 * cam).astype(np.uint8)
                heat_image = Image.fromarray(heat, mode="RGBA")
                overlay = Image.alpha_composite(image.convert("RGBA"), heat_image)
                cam_available = True
                gradcam_url = self._png_data_url(heat_image)
                overlay_url = self._png_data_url(overlay)
            except Exception:
                # Explanation failure must not discard a valid classification.
                cam_available = False
            finally:
                handle.remove()

            scores = {name: float(probabilities[i].detach().cpu()) for i, name in enumerate(CLASS_NAMES)}
            return {
                "analysis_id": uuid.uuid4().hex,
                "predicted_class": CLASS_NAMES[predicted_index],
                "class_scores": scores,
                "model_name": MODEL_NAME,
                "model_architecture": MODEL_ARCHITECTURE,
                "checkpoint": self.checkpoint_path.name,
                "inference_status": "completed",
                "gradcam": {"available": cam_available, "heatmap": gradcam_url, "overlay": overlay_url},
                "disclaimer": DISCLAIMER,
            }
        except BrainModelUnavailable:
            raise
        except Exception as exc:
            raise RuntimeError(f"Brain MRI inference failed: {exc}") from exc
        finally:
            handle.remove()


service = BrainMRIService()
