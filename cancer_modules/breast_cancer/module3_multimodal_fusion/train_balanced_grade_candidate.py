"""Train a versioned class-balanced Module 2 grade model without replacing its artifact.

The source dataset remains in Module 2 and is read-only. The candidate is
validated with patient-grouped folds before fitting on all labeled records.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


HERE = Path(__file__).resolve().parent
DATA_PATH = HERE.parent / "module2_clinical_analysis" / "Clinical_dataset.xlsx.txt"
ARTIFACT_PATH = HERE / "artifacts" / "clinical_grade_balanced_candidate.pkl"
REPORT_PATH = HERE / "reports" / "clinical_grade_balanced_candidate.json"
TARGET = "Neoplasm Histologic Grade"
FEATURES = ["Age at Diagnosis", "Tumor Size", "ER Status", "PR Status", "HER2 Status"]
NUMERIC = ["Age at Diagnosis", "Tumor Size"]
CATEGORICAL = ["ER Status", "PR Status", "HER2 Status"]


def make_pipeline() -> Pipeline:
    preprocess = ColumnTransformer(
        transformers=[
            ("numeric", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]), NUMERIC),
            ("categorical", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]), CATEGORICAL),
        ]
    )
    return Pipeline([
        ("preprocessing", preprocess),
        ("classifier", RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])


def main() -> None:
    frame = pd.read_csv(DATA_PATH, sep="\t")
    frame[TARGET] = pd.to_numeric(frame[TARGET], errors="coerce")
    frame = frame.loc[frame[TARGET].isin([1, 2, 3])].copy()
    frame[TARGET] = frame[TARGET].astype(int)
    if frame["Patient ID"].isna().any():
        raise ValueError("Patient IDs are required for patient-grouped validation.")

    x, y, groups = frame[FEATURES], frame[TARGET], frame["Patient ID"]
    if groups.duplicated().any():
        raise ValueError("Duplicate patient IDs found; review records before training.")

    folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    fold_metrics = []
    for fold, (train_idx, test_idx) in enumerate(folds.split(x, y, groups), start=1):
        model = make_pipeline().fit(x.iloc[train_idx], y.iloc[train_idx])
        predictions = model.predict(x.iloc[test_idx])
        fold_metrics.append({
            "fold": fold,
            "accuracy": float(accuracy_score(y.iloc[test_idx], predictions)),
            "macro_f1": float(f1_score(y.iloc[test_idx], predictions, average="macro", zero_division=0)),
            "recall_by_grade": {
                str(grade): float(value)
                for grade, value in zip(
                    (1, 2, 3),
                    recall_score(y.iloc[test_idx], predictions, labels=[1, 2, 3], average=None, zero_division=0),
                )
            },
        })

    final_model = make_pipeline().fit(x, y)
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, ARTIFACT_PATH)
    summary = {
        "status": "research_candidate_not_clinically_validated",
        "dataset": str(DATA_PATH.name),
        "patient_count": int(groups.nunique()),
        "labeled_record_count": int(len(frame)),
        "class_counts": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
        "patient_grouped_stratified_cv": {
            "fold_count": len(fold_metrics),
            "mean_accuracy": float(sum(row["accuracy"] for row in fold_metrics) / len(fold_metrics)),
            "mean_macro_f1": float(sum(row["macro_f1"] for row in fold_metrics) / len(fold_metrics)),
            "mean_recall_by_grade": {
                str(grade): float(sum(row["recall_by_grade"][str(grade)] for row in fold_metrics) / len(fold_metrics))
                for grade in (1, 2, 3)
            },
            "folds": fold_metrics,
        },
        "class_weight": "balanced",
        "features": FEATURES,
        "target": TARGET,
        "sklearn_version": sklearn.__version__,
        "artifact": ARTIFACT_PATH.name,
        "limitation": "Class-balanced model candidate; modest retrospective metrics do not establish clinical validity.",
    }
    REPORT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
