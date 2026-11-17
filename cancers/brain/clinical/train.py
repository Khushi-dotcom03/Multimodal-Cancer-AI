"""Train/evaluate a leakage-controlled clinical subtype model from IPD-Brain."""

from __future__ import annotations

import json
import platform
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.pipeline import Pipeline

from cancers.brain.clinical.pipeline import (
    CLASSES,
    DEFAULT_DATASET,
    FEATURE_COLUMNS,
    audit_dataset,
    make_preprocessor,
    model_features,
)


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "brain_clinical_pipeline.joblib"
REPORT_PATH = ROOT / "evaluation" / "brain_clinical_metrics.json"


def _metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASSES, zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_recall_fscore_support(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)[0]),
        "macro_recall": float(precision_recall_fscore_support(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)[1]),
        "macro_f1": float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)),
        "per_class": {
            label: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i, label in enumerate(CLASSES)
        },
        "confusion_matrix_labels": CLASSES,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=CLASSES).tolist(),
    }


def _candidate_models() -> dict[str, Pipeline]:
    def pipe(estimator) -> Pipeline:
        return Pipeline([("preprocess", make_preprocessor()), ("model", estimator)])

    return {
        "majority_class_baseline": pipe(DummyClassifier(strategy="most_frequent")),
        "logistic_regression_balanced": pipe(
            LogisticRegression(
                solver="lbfgs", max_iter=2500, class_weight="balanced", C=1.0, random_state=42
            )
        ),
        "random_forest_balanced": pipe(
            RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=2,
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=1,
            )
        ),
        "extra_trees_balanced": pipe(
            ExtraTreesClassifier(
                n_estimators=300,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=42,
                n_jobs=1,
            )
        ),
    }


def train(dataset_path: str | Path = DEFAULT_DATASET) -> dict:
    frame, audit = audit_dataset(dataset_path)
    # Do not train on a record whose pathology narrative explicitly disagrees with Subtype.
    frame = frame.loc[~frame["_diagnosis_conflict"]].reset_index(drop=True)
    X = model_features(frame)
    y = frame["Subtype"].astype(str)
    groups = frame["_patient_group"].astype(str)

    if groups.duplicated().any():
        raise ValueError("Patient group duplicated across records; split audit must be resolved first")

    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    train_indices, test_indices = next(outer.split(X, y, groups))
    x_dev, x_test = X.iloc[train_indices], X.iloc[test_indices]
    y_dev, y_test = y.iloc[train_indices], y.iloc[test_indices]
    g_dev = groups.iloc[train_indices]
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=43)

    models = _candidate_models()
    cv_summary: dict[str, dict] = {}
    for name, model in models.items():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            scores = cross_val_score(
                model,
                x_dev,
                y_dev,
                groups=g_dev,
                cv=cv,
                scoring="f1_macro",
                n_jobs=1,
            )
        cv_summary[name] = {
            "macro_f1_folds": [float(value) for value in scores],
            "mean_macro_f1": float(scores.mean()),
            "std_macro_f1": float(scores.std()),
        }

    baseline_name = "majority_class_baseline"
    selected_name = max(
        (name for name in models if name != baseline_name),
        key=lambda name: cv_summary[name]["mean_macro_f1"],
    )
    selected = models[selected_name]
    selected.fit(x_dev, y_dev)
    selected_predictions = selected.predict(x_test)
    selected_test = _metrics(y_test, selected_predictions)

    baseline = models[baseline_name]
    baseline.fit(x_dev, y_dev)
    baseline_test = _metrics(y_test, baseline.predict(x_test))
    deployment_eligible = (
        cv_summary[selected_name]["mean_macro_f1"] > cv_summary[baseline_name]["mean_macro_f1"]
        and selected_test["macro_f1"] > baseline_test["macro_f1"]
    )

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_audit": audit,
        "training": {
            "records_after_quality_exclusion": int(len(frame)),
            "patient_groups_after_quality_exclusion": int(groups.nunique()),
            "excluded_explicit_diagnosis_conflicts": audit["diagnosis_target_quality"]["explicit_conflict_records"],
            "feature_columns": FEATURE_COLUMNS,
            "target": "Subtype",
            "patient_level_holdout": {
                "splitter": "StratifiedGroupKFold",
                "folds": 5,
                "random_state": 42,
                "train_records": int(len(train_indices)),
                "test_records": int(len(test_indices)),
                "train_patient_groups": int(groups.iloc[train_indices].nunique()),
                "test_patient_groups": int(groups.iloc[test_indices].nunique()),
                "group_overlap": int(len(set(groups.iloc[train_indices]) & set(groups.iloc[test_indices]))),
                "test_class_counts": {str(k): int(v) for k, v in y_test.value_counts().items()},
            },
            "model_selection": {
                "criterion": "highest five-fold development macro-F1",
                "validation_cv": "StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=43)",
                "candidates": cv_summary,
                "selected_model": selected_name,
            },
            "test_metrics": {
                "selected_model": selected_test,
                "majority_class_baseline": baseline_test,
            },
            "deployment_eligible": bool(deployment_eligible),
            "score_note": "Logistic-regression predict_proba outputs are uncalibrated model scores, not calibrated probabilities.",
            "python_version": platform.python_version(),
            "scikit_learn_version": sklearn.__version__,
            "random_states": {"test_split": 42, "validation_cv": 43, "estimators": 42},
        },
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if deployment_eligible:
        final_model = models[selected_name]
        final_model.fit(X, y)
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": final_model, "metadata": report["training"]}, MODEL_PATH)
    elif MODEL_PATH.exists():
        MODEL_PATH.unlink()

    return report


if __name__ == "__main__":
    result = train()
    print(json.dumps({
        "selected_model": result["training"]["model_selection"]["selected_model"],
        "deployment_eligible": result["training"]["deployment_eligible"],
        "validation_cv": result["training"]["model_selection"]["candidates"],
        "test_metrics": result["training"]["test_metrics"],
        "model_path": str(MODEL_PATH) if result["training"]["deployment_eligible"] else None,
        "report_path": str(REPORT_PATH),
    }, indent=2))
