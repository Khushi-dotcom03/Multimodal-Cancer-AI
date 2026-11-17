"""Dataset audit and leakage-controlled feature pipeline for IPD-Brain clinical data."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler


CLASSES = ["GLIOBLASTOMA", "ASTROCYTOMA", "OLIGODENDROGLIOMA"]
DISPLAY_CLASSES = {
    "GLIOBLASTOMA": "Glioblastoma",
    "ASTROCYTOMA": "Astrocytoma",
    "OLIGODENDROGLIOMA": "Oligodendroglioma",
}
FEATURE_COLUMNS = ["Age", "Sex", "SITE"]
REQUIRED_COLUMNS = ["Case Number", "Age", "Sex", "C/F", "Radiology", "Diagnosis", "WHO Grade", "SITE", "Subtype", "ki67(in %)", "IDH1R132H", "ATRX", "p53"]
DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "data" / "brain cancer" / "IPD_Brain.csv"

_DIAGNOSIS_PATTERNS = {
    "GLIOBLASTOMA": re.compile(r"glioblastoma|gliomablastoma|\bgbm\b", re.I),
    "ASTROCYTOMA": re.compile(r"astrocytoma", re.I),
    "OLIGODENDROGLIOMA": re.compile(r"oligodendroglioma", re.I),
}
_TARGET_PATTERNS = re.compile(r"glioblastoma|gliomablastoma|\bgbm\b|astrocytoma|oligodendroglioma", re.I)
_GENERAL_PATHOLOGY_PATTERNS = re.compile(r"glioma|tumou?r|neoplasm|malignan|metasta|biopsy|hpe|histopath", re.I)


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"IPD-Brain clinical CSV not found: {path}")
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            frame = pd.read_csv(path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - latin1 always decodes bytes
        raise ValueError("Could not decode the IPD-Brain CSV")
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"IPD-Brain CSV is missing required columns: {', '.join(missing_columns)}")
    return frame


def _diagnosis_label(value: object) -> str | None:
    text = "" if pd.isna(value) else str(value)
    matches = [label for label, pattern in _DIAGNOSIS_PATTERNS.items() if pattern.search(text)]
    return matches[0] if len(matches) == 1 else None


def patient_groups(case_numbers: pd.Series) -> pd.Series:
    groups = case_numbers.fillna("").astype(str).str.extract(r"(?i)brain[- ]?(\d+)", expand=False)
    if groups.isna().any():
        raise ValueError("Could not derive patient groups from every Case Number")
    return "IPD-Brain-" + groups.astype(str)


def clean_site(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = text.casefold().replace("?", " ")
    text = re.sub(r"\b(?:lobe|lobes|region|area|gyrus|lesion|site)\b", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def flatten_text(values) -> np.ndarray:
    return np.asarray(values, dtype=object).reshape(-1).astype(str)


def audit_dataset(path: str | Path = DEFAULT_DATASET) -> tuple[pd.DataFrame, dict]:
    frame = _read_csv(path)
    frame["Subtype"] = frame["Subtype"].fillna("").astype(str).str.strip().str.upper()
    unexpected = sorted(set(frame["Subtype"]) - set(CLASSES))
    if frame["Subtype"].eq("").any() or unexpected:
        raise ValueError(f"Unexpected or missing Subtype labels: {unexpected}")

    groups = patient_groups(frame["Case Number"])
    diagnosis_labels = frame["Diagnosis"].map(_diagnosis_label)
    diagnosis_conflict = diagnosis_labels.notna() & diagnosis_labels.ne(frame["Subtype"])
    diagnosis_unspecific = diagnosis_labels.isna()

    text_audit = {}
    for column in ("C/F", "Radiology"):
        text = frame[column].fillna("").astype(str)
        text_audit[column] = {
            "populated": int(text.str.strip().ne("").sum()),
            "missing": int(frame[column].isna().sum()),
            "unique_nonempty": int(text[text.str.strip().ne("")].nunique()),
            "median_characters": float(text[text.str.strip().ne("")].str.len().median()),
            "records_with_explicit_subtype_terms": int(text.str.contains(_TARGET_PATTERNS, na=False).sum()),
            "records_with_general_tumor_or_pathology_terms": int(text.str.contains(_GENERAL_PATHOLOGY_PATTERNS, na=False).sum()),
        }

    audit = {
        "dataset": "IPD-Brain clinical records",
        "path": "data/brain cancer/IPD_Brain.csv",
        "record_count": int(len(frame)),
        "unique_patient_groups": int(groups.nunique()),
        "duplicate_case_number_count": int(frame["Case Number"].duplicated().sum()),
        "duplicate_patient_group_rows": int(groups.duplicated().sum()),
        "duplicate_exact_rows": int(frame.duplicated().sum()),
        "columns": list(frame.columns),
        "missing_by_column": {str(k): int(v) for k, v in frame.isna().sum().items()},
        "age": {
            "minimum": float(frame["Age"].min()),
            "maximum": float(frame["Age"].max()),
            "median": float(frame["Age"].median()),
            "mean": float(frame["Age"].mean()),
        },
        "sex_counts": {str(k): int(v) for k, v in frame["Sex"].value_counts(dropna=False).items()},
        "subtype_counts": {str(k): int(v) for k, v in frame["Subtype"].value_counts(dropna=False).items()},
        "site": {
            "populated": int(frame["SITE"].notna().sum()),
            "missing": int(frame["SITE"].isna().sum()),
            "unique_raw_values": int(frame["SITE"].nunique(dropna=True)),
            "unknown_marker_count": int(frame["SITE"].fillna("").astype(str).str.contains(r"^\s*\?", regex=True).sum()),
        },
        "free_text": text_audit,
        "diagnosis_target_quality": {
            "explicit_conflict_records": int(diagnosis_conflict.sum()),
            "records_without_unambiguous_subtype_in_diagnosis": int(diagnosis_unspecific.sum()),
        },
        "feature_selection": {
            "included": FEATURE_COLUMNS,
            "excluded": {
                "Case Number": "identifier used only to group records for patient-level split",
                "C/F": "free text includes known/recurrent tumor and subtype references in some rows",
                "Radiology": "contains direct suspected/confirmed subtype terms in many rows",
                "Diagnosis": "pathology-derived label and explicit subtype information",
                "WHO Grade": "pathology-derived label and correlated target information",
                "Subtype": "target only",
                "ki67(in %)": "pathology-derived molecular/proliferation marker",
                "IDH1R132H": "molecular pathology marker",
                "ATRX": "molecular pathology marker",
                "p53": "molecular pathology marker",
            },
        },
        "target": "Subtype (Glioblastoma, Astrocytoma, Oligodendroglioma) among IPD-Brain glioma patients",
        "limitations": [
            "328 patient records from a retrospective, single-institution Indian cohort; no external validation cohort is supplied here.",
            "Site is populated for nearly all records but appears in 187 differently written values and requires free-text normalization.",
            "C/F and Radiology were not used because they can disclose prior/pathology subtype information.",
        ],
    }
    frame = frame.copy()
    frame["_patient_group"] = groups.to_numpy()
    frame["_diagnosis_conflict"] = diagnosis_conflict.to_numpy()
    frame["_diagnosis_unspecific"] = diagnosis_unspecific.to_numpy()
    return frame, audit


def make_preprocessor() -> ColumnTransformer:
    age = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    sex = make_pipeline(
        SimpleImputer(strategy="most_frequent"),
        OneHotEncoder(handle_unknown="ignore"),
    )
    site_text = make_pipeline(
        FunctionTransformer(flatten_text, validate=False),
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
    )
    return ColumnTransformer(
        [
            ("age", age, ["Age"]),
            ("sex", sex, ["Sex"]),
            ("site", site_text, ["SITE"]),
        ],
        remainder="drop",
    )


def model_features(frame: pd.DataFrame) -> pd.DataFrame:
    features = frame[FEATURE_COLUMNS].copy()
    features["Age"] = pd.to_numeric(features["Age"], errors="coerce")
    features["Sex"] = features["Sex"].fillna("").astype(str).str.strip().str.upper()
    features["SITE"] = features["SITE"].map(clean_site)
    return features
