"""PAD-UFES-20 clinical-only preprocessing utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CLINICAL_FEATURES = [
    "age",
    "region",
    "itch",
    "grew",
    "hurt",
    "changed",
    "bleed",
    "elevation",
]

NUMERIC_FEATURES = ["age"]
CATEGORICAL_FEATURES = [
    "region",
    "itch",
    "grew",
    "hurt",
    "changed",
    "bleed",
    "elevation",
]

TARGET_COLUMN = "diagnostic"
SPLIT_COLUMN = "split"
PATIENT_COLUMN = "patient_group"
LESION_COLUMN = "lesion_id"

VALID_SPLITS = {"train", "validation", "test"}


def _clean_category(value: object) -> str:
    """Keep UNK distinct from False; represent blank values as UNK."""
    if pd.isna(value):
        return "UNK"

    cleaned = str(value).strip()
    if not cleaned or cleaned.casefold() in {"nan", "none"}:
        return "UNK"

    if cleaned.casefold() == "unk":
        return "UNK"

    if cleaned.casefold() == "true":
        return "True"

    if cleaned.casefold() == "false":
        return "False"

    return cleaned.upper()


def build_lesion_table(
    matched_csv: str | Path,
    output_csv: str | Path | None = None,
) -> pd.DataFrame:
    """
    Create one row per patient-lesion pair.

    The original matched_images.csv is read-only and is never overwritten.
    Every feature, diagnosis and split must be consistent within a lesion.
    """
    matched_csv = Path(matched_csv)

    if not matched_csv.is_file():
        raise FileNotFoundError(f"Matched dataset not found: {matched_csv}")

    df = pd.read_csv(matched_csv, dtype={"lesion_id": "string"})

    required = (
        CLINICAL_FEATURES
        + [TARGET_COLUMN, SPLIT_COLUMN, PATIENT_COLUMN, LESION_COLUMN]
    )
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(f"Required columns missing from dataset: {missing}")

    if df.empty:
        raise ValueError("Matched dataset contains no rows.")

    df[PATIENT_COLUMN] = df[PATIENT_COLUMN].astype("string").str.strip()
    df[LESION_COLUMN] = df[LESION_COLUMN].astype("string").str.strip()

    if df[[PATIENT_COLUMN, LESION_COLUMN]].isna().any().any():
        raise ValueError("Patient or lesion identifiers contain missing values.")

    if (
        df[PATIENT_COLUMN].eq("").any()
        or df[LESION_COLUMN].eq("").any()
    ):
        raise ValueError("Patient or lesion identifiers contain blank values.")

    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(str).str.strip().str.upper()
    df[SPLIT_COLUMN] = df[SPLIT_COLUMN].astype(str).str.strip().str.lower()

    unexpected_splits = set(df[SPLIT_COLUMN].unique()) - VALID_SPLITS
    if unexpected_splits:
        raise ValueError(f"Unexpected split values: {sorted(unexpected_splits)}")

    # Composite key is essential because lesion_id alone can repeat
    # across different patients.
    df["lesion_key"] = (
        df[PATIENT_COLUMN].astype(str)
        + "_"
        + df[LESION_COLUMN].astype(str)
    )

    # Clean feature values without merging UNK into False.
    df["age"] = pd.to_numeric(df["age"], errors="coerce")

    for column in CATEGORICAL_FEATURES:
        df[column] = df[column].map(_clean_category)

    # Every record belonging to a lesion must agree on features,
    # diagnosis and split before one representative row is selected.
    consistency_columns = CLINICAL_FEATURES + [
        TARGET_COLUMN,
        SPLIT_COLUMN,
        PATIENT_COLUMN,
    ]

    inconsistent = []

    for column in consistency_columns:
        counts = df.groupby("lesion_key", dropna=False)[column].nunique(
            dropna=False
        )
        bad_keys = counts[counts > 1].index.tolist()

        if bad_keys:
            inconsistent.append((column, bad_keys[:5]))

    if inconsistent:
        details = "; ".join(
            f"{column}: {keys}"
            for column, keys in inconsistent
        )
        raise ValueError(
            "Conflicting records found within the same patient-lesion. "
            f"Resolve the data issue before training. {details}"
        )

    lesions = (
        df.drop_duplicates(subset=["lesion_key"], keep="first")
        .loc[
            :,
            [
                "lesion_key",
                PATIENT_COLUMN,
                LESION_COLUMN,
                *CLINICAL_FEATURES,
                TARGET_COLUMN,
                SPLIT_COLUMN,
            ],
        ]
        .reset_index(drop=True)
    )

    if lesions["lesion_key"].duplicated().any():
        raise AssertionError("Lesion-level table still contains duplicates.")

    if lesions[CLINICAL_FEATURES].isna().all(axis=1).any():
        raise ValueError("At least one lesion has no usable clinical features.")

    if output_csv is not None:
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        lesions.to_csv(output_csv, index=False)

    return lesions


def create_clinical_preprocessor() -> ColumnTransformer:
    """
    Create preprocessing pipelines.

    IMPORTANT: call fit() only on the training split.
    Validation and test data must only use transform().
    """
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                    dtype="float32",
                ),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def get_split_data(
    lesions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return train, validation and test data without refitting anything."""
    result = {}

    for split in ("train", "validation", "test"):
        subset = lesions.loc[lesions[SPLIT_COLUMN] == split].copy()

        if subset.empty:
            raise ValueError(f"The {split} split is empty.")

        result[split] = subset.reset_index(drop=True)

    # Explicitly ensure patient groups do not cross splits.
    patient_sets = {
        split: set(frame[PATIENT_COLUMN].astype(str))
        for split, frame in result.items()
    }

    if patient_sets["train"] & patient_sets["validation"]:
        raise ValueError("Patient leakage between train and validation.")

    if patient_sets["train"] & patient_sets["test"]:
        raise ValueError("Patient leakage between train and test.")

    if patient_sets["validation"] & patient_sets["test"]:
        raise ValueError("Patient leakage between validation and test.")

    return result["train"], result["validation"], result["test"]
