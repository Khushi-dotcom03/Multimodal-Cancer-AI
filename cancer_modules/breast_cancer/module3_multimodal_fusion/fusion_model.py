"""Small-sample paired image/clinical late-fusion models for BrEaST."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CLINICAL_COLUMNS = ("age", "tissue_composition", "signs", "symptoms")
LEAKAGE_COLUMNS = {
    "diagnosis", "interpretation", "verification", "label", "classification",
    "birads", "case_id", "patient_id", "tumor_mask_filenames", "other_mask_filenames",
}
IMAGE_SIZE = 48
CELL_SIZE = 8
ORIENTATION_BINS = 9


def normalize_clinical_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize the four allowed BrEaST inputs; never infer target fields."""
    missing = set(CLINICAL_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Clinical input is missing columns: {sorted(missing)}")
    result = frame.loc[:, list(CLINICAL_COLUMNS)].copy()
    age = result["age"].map(
        lambda value: np.nan
        if isinstance(value, str) and value.strip().casefold() in {"", "not available", "n/a", "na", "unknown"}
        else value
    )
    result["age"] = pd.to_numeric(age, errors="coerce")
    for column in CLINICAL_COLUMNS[1:]:
        values = result[column].astype(object).where(result[column].notna(), np.nan)
        values = pd.Series(values, index=result.index).map(lambda value: value.strip() if isinstance(value, str) else value)
        missing_mask = values.map(lambda value: isinstance(value, str) and value.casefold() in {"", "not available", "n/a", "na", "unknown"})
        result[column] = values.mask(missing_mask, np.nan)
    return result


class UltrasoundHOGVectorizer(BaseEstimator, TransformerMixin):
    """Compact grayscale HOG descriptor with no external pretrained weights."""

    def __init__(self, image_size: int = IMAGE_SIZE, cell_size: int = CELL_SIZE, orientation_bins: int = ORIENTATION_BINS):
        self.image_size = image_size
        self.cell_size = cell_size
        self.orientation_bins = orientation_bins

    def fit(self, X: Any, y: Any = None) -> "UltrasoundHOGVectorizer":
        del X, y
        return self

    def transform(self, X: Any) -> np.ndarray:
        paths = self._paths(X)
        return np.vstack([self._describe(path) for path in paths]).astype(np.float32, copy=False)

    @staticmethod
    def _paths(X: Any) -> list[str]:
        if isinstance(X, pd.DataFrame):
            if "image_path" not in X:
                raise ValueError("Image model input requires image_path.")
            values = X["image_path"].tolist()
        elif isinstance(X, pd.Series):
            values = X.tolist()
        else:
            values = list(X)
        return [str(value) for value in values]

    def _describe(self, image_path: str) -> np.ndarray:
        with Image.open(image_path) as source:
            image = np.asarray(
                source.convert("L").resize((self.image_size, self.image_size), Image.Resampling.BILINEAR),
                dtype=np.float32,
            ) / 255.0
        gy, gx = np.gradient(image)
        magnitude = np.hypot(gx, gy)
        angle = np.mod(np.degrees(np.arctan2(gy, gx)), 180.0)
        cells = self.image_size // self.cell_size
        histograms = np.zeros((cells, cells, self.orientation_bins), dtype=np.float32)
        bin_width = 180.0 / self.orientation_bins
        bin_indices = np.floor(angle / bin_width).astype(np.int32) % self.orientation_bins
        for row in range(cells):
            for col in range(cells):
                r0, c0 = row * self.cell_size, col * self.cell_size
                local_bins = bin_indices[r0:r0 + self.cell_size, c0:c0 + self.cell_size].ravel()
                local_mag = magnitude[r0:r0 + self.cell_size, c0:c0 + self.cell_size].ravel()
                histograms[row, col] = np.bincount(
                    local_bins, weights=local_mag, minlength=self.orientation_bins
                )[:self.orientation_bins]
        blocks = []
        for row in range(cells - 1):
            for col in range(cells - 1):
                block = histograms[row:row + 2, col:col + 2].ravel()
                blocks.append(block / (np.linalg.norm(block) + 1e-6))
        return np.concatenate(blocks)


def make_image_pipeline() -> Pipeline:
    return Pipeline([
        ("hog", UltrasoundHOGVectorizer()),
        ("scale", StandardScaler()),
        ("classifier", LogisticRegression(C=0.03, class_weight="balanced", max_iter=2000, solver="liblinear", random_state=42)),
    ])


def make_clinical_pipeline() -> Pipeline:
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="(missing)")),
        ("one_hot", OneHotEncoder(handle_unknown="ignore", min_frequency=2)),
    ])
    preprocess = ColumnTransformer([
        ("age", numeric, ["age"]),
        ("clinical", categorical, list(CLINICAL_COLUMNS[1:])),
    ])
    return Pipeline([
        ("preprocess", preprocess),
        ("classifier", LogisticRegression(C=0.1, class_weight="balanced", max_iter=2000, solver="liblinear", random_state=42)),
    ])


def positive_score(estimator: Any, X: Any) -> np.ndarray:
    probabilities = estimator.predict_proba(X)
    classes = list(estimator.classes_)
    if 1 not in classes:
        raise ValueError("Expected malignant class label 1 in fitted estimator.")
    return np.asarray(probabilities)[:, classes.index(1)]


class PairedLateFusionModel:
    """L2-regularized stacker trained only from paired, out-of-fold branch scores."""

    def __init__(self, inner_folds: int = 4, random_state: int = 42):
        self.inner_folds = inner_folds
        self.random_state = random_state
        self.image_model = make_image_pipeline()
        self.clinical_model = make_clinical_pipeline()
        self.fusion_model = LogisticRegression(
            C=0.1, class_weight="balanced", max_iter=2000, solver="liblinear", random_state=random_state
        )
        self.classes_ = np.asarray([0, 1])

    def fit(self, X: pd.DataFrame, y: Any) -> "PairedLateFusionModel":
        required = {"case_id", "image_path", *CLINICAL_COLUMNS}
        missing = required - set(X.columns)
        if missing:
            raise ValueError(f"Paired training data is missing fields: {sorted(missing)}")
        if X["case_id"].isna().any() or X["case_id"].duplicated().any():
            raise ValueError("Training requires exactly one row per unique official CaseID.")
        targets = np.asarray(y, dtype=np.int32)
        if set(np.unique(targets)) != {0, 1}:
            raise ValueError("Training target must include both benign=0 and malignant=1.")
        if len(X) < self.inner_folds * 2:
            raise ValueError("Not enough paired cases for the configured grouped out-of-fold fusion training.")

        image_X = X[["image_path"]].reset_index(drop=True)
        clinical_X = normalize_clinical_frame(X.reset_index(drop=True))
        groups = X["case_id"].astype(str).to_numpy()
        splitter = StratifiedGroupKFold(n_splits=self.inner_folds, shuffle=True, random_state=self.random_state)
        image_oof = np.full(len(X), np.nan, dtype=np.float64)
        clinical_oof = np.full(len(X), np.nan, dtype=np.float64)
        for train_index, valid_index in splitter.split(X, targets, groups=groups):
            image_fold = clone(self.image_model).fit(image_X.iloc[train_index], targets[train_index])
            clinical_fold = clone(self.clinical_model).fit(clinical_X.iloc[train_index], targets[train_index])
            image_oof[valid_index] = positive_score(image_fold, image_X.iloc[valid_index])
            clinical_oof[valid_index] = positive_score(clinical_fold, clinical_X.iloc[valid_index])
        if not np.isfinite(image_oof).all() or not np.isfinite(clinical_oof).all():
            raise RuntimeError("Out-of-fold paired branch scores are incomplete.")
        self.fusion_model.fit(np.column_stack([image_oof, clinical_oof]), targets)
        self.image_model.fit(image_X, targets)
        self.clinical_model.fit(clinical_X, targets)
        self.training_case_count_ = int(len(X))
        self.training_group_count_ = int(pd.Series(groups).nunique())
        return self

    def predict_branch_scores(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        image_X = X[["image_path"]].reset_index(drop=True)
        clinical_X = normalize_clinical_frame(X.reset_index(drop=True))
        return {
            "image": positive_score(self.image_model, image_X),
            "clinical": positive_score(self.clinical_model, clinical_X),
        }

    def predict_fusion_score(self, image_score: Any, clinical_score: Any) -> np.ndarray:
        paired = np.column_stack([np.asarray(image_score), np.asarray(clinical_score)])
        return positive_score(self.fusion_model, paired)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        scores = self.predict_branch_scores(X)
        return self.fusion_model.predict_proba(np.column_stack([scores["image"], scores["clinical"]]))

\n