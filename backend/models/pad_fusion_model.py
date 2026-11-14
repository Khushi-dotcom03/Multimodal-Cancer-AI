"""PAD-UFES-20 image and clinical feature-level fusion model."""

import torch
from torch import nn
from torchvision.models import resnet18


class PADFusionModel(nn.Module):
    def __init__(self, clinical_features: int, num_classes: int = 6):
        super().__init__()
        self.image_encoder = resnet18(weights=None)
        self.image_encoder.fc = nn.Identity()
        self.clinical_encoder = nn.Sequential(
            nn.Linear(clinical_features, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU(),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.35), nn.Linear(512 + 32, 128), nn.ReLU(),
            nn.Dropout(0.3), nn.Linear(128, num_classes),
        )

    def forward(self, image: torch.Tensor, clinical: torch.Tensor) -> torch.Tensor:
        image_features = self.image_encoder(image)
        clinical_features = self.clinical_encoder(clinical)
        return self.classifier(torch.cat((image_features, clinical_features), dim=1))
