"""Fold-local clinical preprocessing and deterministic MRI slice sampling."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from torchvision import transforms

from cancers.brain.multimodal.config import CLINICAL_CATEGORICAL, CLINICAL_NUMERIC, IMAGE_SIZE

MRI_IMAGE_TRANSFORM = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def make_clinical_preprocessor() -> ColumnTransformer:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median", keep_empty_features=True)), ("scale", StandardScaler())])
    categorical = Pipeline([("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    return ColumnTransformer([("numeric", numeric, CLINICAL_NUMERIC), ("categorical", categorical, CLINICAL_CATEGORICAL)], sparse_threshold=0)


def clinical_frame(frame: pd.DataFrame) -> pd.DataFrame:
    values = frame[CLINICAL_NUMERIC + CLINICAL_CATEGORICAL].copy()
    for col in CLINICAL_NUMERIC:
        values[col] = pd.to_numeric(values[col], errors="coerce")
    for col in CLINICAL_CATEGORICAL:
        cleaned = values[col].astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
        # scikit-learn imputers expect np.nan rather than pandas' scalar pd.NA.
        values[col] = cleaned.astype(object).where(cleaned.notna(), np.nan)
    return values


def select_slice_paths(paths: list[str], count: int) -> list[str]:
    if not paths:
        raise ValueError("Patient has no readable MRI slices")
    indices = np.linspace(0, len(paths) - 1, min(count, len(paths)), dtype=int)
    return [paths[i] for i in indices]
