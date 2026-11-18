"""Inference helper for the Feature 1 skin-scope gate."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import joblib
import torch

try:
    from . import fusion_utils as fu
except ImportError:  # pragma: no cover - `uvicorn api:app` from backend/
    import fusion_utils as fu


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=4)
def _load_gate(model_dir: str, checkpoint_path: str, checkpoint_mtime: int, checkpoint_size: int):
    artifact = Path(model_dir) / "skin_ood" / "skin_ood_gate.joblib"
    if not artifact.is_file():
        raise FileNotFoundError(f"Skin OOD gate artifact is missing: {artifact}")
    package = joblib.load(artifact)
    expected_hash = package.get("hamCheckpointSha256")
    actual_hash = _sha256(Path(checkpoint_path))
    if not expected_hash or expected_hash != actual_hash:
        raise ValueError("Skin OOD gate was trained with a different HAM10000 checkpoint")
    if not hasattr(package.get("classifier"), "decision_function"):
        raise ValueError("Skin OOD gate classifier is invalid")
    if not isinstance(package.get("threshold"), (int, float)):
        raise ValueError("Skin OOD gate threshold is invalid")
    return package


def score_skin_scope(image, backbone, model_dir: Path, device: str) -> tuple[bool, float]:
    """Return whether an image is in scope and its trained-gate decision score."""
    checkpoint = Path(model_dir) / "resnet18_best.pth"
    stat = checkpoint.stat()
    package = _load_gate(str(Path(model_dir).resolve()), str(checkpoint.resolve()),
                         stat.st_mtime_ns, stat.st_size)
    tensor = fu.EVAL_TF(image.convert("RGB")).unsqueeze(0).to(device)
    with torch.inference_mode():
        features = backbone(tensor).flatten(1).cpu().numpy()
    score = float(package["classifier"].decision_function(features)[0])
    return score >= float(package["threshold"]), score
