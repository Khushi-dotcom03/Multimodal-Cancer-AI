"""Train/evaluate paired BrEaST image, clinical, and late-fusion models."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold

from .fusion_model import PairedLateFusionModel


MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = MODULE_DIR / "data" / "processed" / "paired_cases.csv"
DEFAULT_MODEL = MODULE_DIR / "artifacts" / "breast_paired_fusion.joblib"
DEFAULT_REPORT = MODULE_DIR / "reports" / "fusion_evaluation.json"


def _metrics(y_true: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    predictions = (scores >= 0.5).astype(np.int32)
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    return {
        "threshold": 0.5,
        "sensitivity_malignant": float(recall_score(y_true, predictions, pos_label=1, zero_division=0)),
        "specificity_benign": float(recall_score(y_true, predictions, pos_label=0, zero_division=0)),
        "f1_malignant": float(f1_score(y_true, predictions, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) == 2 else None,
        "confusion_matrix_labels": ["Benign", "Malignant"],
        "confusion_matrix_rows_true_columns_predicted": matrix.astype(int).tolist(),
        "class_counts": {
            "benign": int(np.sum(y_true == 0)),
            "malignant": int(np.sum(y_true == 1)),
        },
        "prediction_counts": {
            "benign": int(np.sum(predictions == 0)),
            "malignant": int(np.sum(predictions == 1)),
        },
    }


def evaluate_nested_group_cv(data: pd.DataFrame, *, outer_folds: int = 5, inner_folds: int = 4) -> dict[str, Any]:
    """Outer patient-grouped CV; stacker branch scores are inner out-of-fold only."""
    if data["case_id"].duplicated().any():
        raise ValueError("Expected one paired record per official CaseID; duplicate groups are not accepted.")
    binary = data.loc[data["label"].isin(["benign", "malignant"])].reset_index(drop=True)
    y = binary["label"].map({"benign": 0, "malignant": 1}).to_numpy(dtype=np.int32)
    groups = binary["case_id"].astype(str).to_numpy()
    if len(np.unique(y)) != 2 or min(np.bincount(y)) < outer_folds:
        raise ValueError("Insufficient cases per class for the requested outer grouped folds.")
    splitter = StratifiedGroupKFold(n_splits=outer_folds, shuffle=True, random_state=42)
    scores = {name: np.full(len(binary), np.nan, dtype=float) for name in ("image", "clinical", "fusion")}
    folds = []

    for fold_index, (train_indices, test_indices) in enumerate(splitter.split(binary, y, groups=groups), start=1):
        train_groups = set(groups[train_indices])
        test_groups = set(groups[test_indices])
        if train_groups & test_groups:
            raise RuntimeError(f"Patient leakage detected in outer fold {fold_index}.")
        model = PairedLateFusionModel(inner_folds=inner_folds, random_state=42 + fold_index)
        model.fit(binary.iloc[train_indices], y[train_indices])
        branch_scores = model.predict_branch_scores(binary.iloc[test_indices])
        fold_fusion = model.predict_fusion_score(branch_scores["image"], branch_scores["clinical"])
        scores["image"][test_indices] = branch_scores["image"]
        scores["clinical"][test_indices] = branch_scores["clinical"]
        scores["fusion"][test_indices] = fold_fusion
        folds.append({
            "fold": fold_index,
            "train_patients": len(train_groups),
            "test_patients": len(test_groups),
            "train_class_counts": {
                "benign": int(np.sum(y[train_indices] == 0)),
                "malignant": int(np.sum(y[train_indices] == 1)),
            },
            "test_class_counts": {
                "benign": int(np.sum(y[test_indices] == 0)),
                "malignant": int(np.sum(y[test_indices] == 1)),
            },
            "patient_overlap": False,
        })

    if any(not np.isfinite(values).all() for values in scores.values()):
        raise RuntimeError("Grouped cross-validation did not produce a score for every case.")
    return {
        "method": f"{outer_folds}-fold StratifiedGroupKFold by official CaseID; {inner_folds}-fold grouped OOF stacking within each training fold",
        "threshold_note": "0.5 is a fixed exploratory display threshold, not a clinically selected operating point.",
        "outer_patient_folds": folds,
        "models": {name: _metrics(y, values) for name, values in scores.items()},
        "calibration": {
            "calibrated": False,
            "assessment": "Not performed; out-of-fold scores from this small single cohort are not an independent calibration set.",
        },
    }


def train(manifest_path: Path, model_path: Path, report_path: Path, *, outer_folds: int = 5, inner_folds: int = 4) -> dict[str, Any]:
    raise RuntimeError(
        "This BrEaST-specific fusion experiment is disabled for the active Module 3 workflow. "
        "BrEaST lacks Tumor Size, ER Status, PR Status, and HER2 Status required by Module 2; "
        "do not train or report this as Module 1 + Module 2 fusion. The previous artifact and "
        "evaluation report are retained for audit and are not used by the active API."
    )

    for path in (model_path, report_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing training output: {path}")
    data = pd.read_csv(manifest_path, dtype={"case_id": str})
    required = {"case_id", "image_path", "age", "tissue_composition", "signs", "symptoms", "label"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Prepared paired manifest lacks required fields: {sorted(missing)}")
    if data["case_id"].isna().any() or data["case_id"].duplicated().any():
        raise ValueError("Training stopped: each official CaseID must appear exactly once.")
    if not data["image_path"].map(lambda path: Path(path).is_file()).all():
        raise FileNotFoundError("Training stopped: at least one officially mapped image file is missing.")
    if not data["label"].isin({"benign", "malignant", "normal"}).all():
        raise ValueError("Training stopped: unexpected label found in prepared dataset.")

    binary = data.loc[data["label"].isin(["benign", "malignant"])].copy().reset_index(drop=True)
    if set(binary.label) != {"benign", "malignant"}:
        raise ValueError("Training stopped: both binary classes must be present.")
    evaluation = evaluate_nested_group_cv(binary, outer_folds=outer_folds, inner_folds=inner_folds)
    y = binary.label.map({"benign": 0, "malignant": 1}).to_numpy(dtype=np.int32)
    final_model = PairedLateFusionModel(inner_folds=outer_folds, random_state=42).fit(binary, y)

    report: dict[str, Any] = {
        "dataset": "BrEaST / TCIA Breast-Lesions-USG",
        "task": "Binary lesion classification: malignant=1 vs benign=0",
        "dataset_citation": "Pawlowska et al., Scientific Data 11, 148 (2024), DOI 10.1038/s41597-024-02984-z; TCIA DOI 10.7937/9WKK-Q141",
        "license": "CC BY 4.0; attribution required; follow TCIA Data Usage Policy",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "patient_count_all_labels": int(data.case_id.nunique()),
        "binary_patient_count": int(binary.case_id.nunique()),
        "normal_cases_excluded_from_binary_training": int((data.label == "normal").sum()),
        "training_class_counts": {
            "benign": int((binary.label == "benign").sum()),
            "malignant": int((binary.label == "malignant").sum()),
        },
        "clinical_inputs": ["Age", "Tissue_composition", "Signs", "Symptoms"],
        "excluded_target_leakage_fields": ["BIRADS", "Interpretation", "Verification", "Diagnosis", "Classification"],
        "evaluation": evaluation,
        "calibration": {
            "calibrated": False,
            "probability_claim_permitted": False,
            "production_or_clinical_validation": False,
            "display_label": "Experimental risk score (uncalibrated)",
        },
        "limitations": [
            "Small, single public cohort; cross-validation is internal and not external validation.",
            "Only four normal cases; normal-class performance was not estimated.",
            "The model score is uncalibrated and must not be represented as a cancer probability or diagnosis.",
            "At inference, paired-case identity is user-attested and cannot be independently verified by this application.",
        ],
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, model_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--outer-folds", type=int, default=5)
    parser.add_argument("--inner-folds", type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(train(args.manifest, args.model_out, args.report_out, outer_folds=args.outer_folds, inner_folds=args.inner_folds), indent=2))


if __name__ == "__main__":
    main()
