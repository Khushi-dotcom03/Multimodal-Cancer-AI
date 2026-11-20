"""Frozen EfficientNet MRI encoder and patient-level classification heads."""

from __future__ import annotations

import torch
from torch import nn
from torchvision import models


def build_pretrained_effnet(checkpoint_path: str, device: torch.device) -> nn.Module:
    """Load the project's pretrained EfficientNet-B0 checkpoint, then expose 1280-D features."""
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 4)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        checkpoint = checkpoint["state_dict"]
    if checkpoint and next(iter(checkpoint)).startswith("module."):
        checkpoint = {key.removeprefix("module."): val for key, val in checkpoint.items()}
    model.load_state_dict(checkpoint, strict=True)
    model.classifier = nn.Identity()
    model.eval().to(device)
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model


class ClinicalMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 32, classes: int = 2):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Dropout(0.25), nn.Linear(hidden_dim, 16), nn.ReLU())
        self.classifier = nn.Linear(16, classes)

    def forward(self, clinical):
        return self.classifier(self.encoder(clinical))


class MRIHead(nn.Module):
    def __init__(self, input_dim: int = 1280, classes: int = 2):
        super().__init__()
        self.classifier = nn.Sequential(nn.Linear(input_dim, 64), nn.ReLU(), nn.Dropout(0.35), nn.Linear(64, classes))

    def forward(self, mri):
        return self.classifier(mri)


class FusionModel(nn.Module):
    def __init__(self, clinical_dim: int, mri_dim: int = 1280, classes: int = 2):
        super().__init__()
        self.clinical_encoder = nn.Sequential(nn.Linear(clinical_dim, 32), nn.ReLU(), nn.Dropout(0.25), nn.Linear(32, 16), nn.ReLU())
        self.mri_encoder = nn.Sequential(nn.Linear(mri_dim, 64), nn.ReLU(), nn.Dropout(0.35))
        self.fusion = nn.Sequential(nn.Linear(80, 32), nn.ReLU(), nn.Dropout(0.35), nn.Linear(32, classes))

    def forward(self, mri, clinical):
        mri_embedding = self.mri_encoder(mri)
        clinical_embedding = self.clinical_encoder(clinical)
        return self.fusion(torch.cat([mri_embedding, clinical_embedding], dim=1))
