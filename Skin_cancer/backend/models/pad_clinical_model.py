"""Clinical-only neural network for PAD-UFES-20."""

import torch
import torch.nn as nn


class PADClinicalMLP(nn.Module):
    """MLP for six-class PAD-UFES-20 clinical classification."""

    def __init__(
        self,
        input_features: int,
        num_classes: int = 6,
        dropout: float = 0.30,
    ):
        super().__init__()

        if input_features <= 0:
            raise ValueError("input_features must be greater than zero.")

        if num_classes <= 1:
            raise ValueError("num_classes must be greater than one.")

        self.input_features = input_features
        self.num_classes = num_classes

        self.network = nn.Sequential(
            nn.Linear(input_features, 128),
            nn.ReLU(),
            nn.LayerNorm(128),
            nn.Dropout(dropout),

            nn.Linear(128, 64),
            nn.ReLU(),
            nn.LayerNorm(64),
            nn.Dropout(dropout),

            nn.Linear(64, 32),
            nn.ReLU(),

            nn.Linear(32, num_classes),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        if features.ndim != 2:
            raise ValueError("Input must have shape [batch_size, features].")

        if features.shape[1] != self.input_features:
            raise ValueError(
                f"Expected {self.input_features} features, "
                f"received {features.shape[1]}."
            )

        return self.network(features)

