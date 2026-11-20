"""Clinical-only MLP architecture matching clinical_mlp_best.pth."""

import torch.nn as nn


class ClinicalMLP(nn.Module):
    def __init__(self, input_features: int = 19, embedding_features: int = 32, classes: int = 7):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_features, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, embedding_features), nn.ReLU(),
        )
        self.head = nn.Linear(embedding_features, classes)

    def forward(self, features):
        return self.head(self.encoder(features))
