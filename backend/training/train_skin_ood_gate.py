"""Train and evaluate a skin-scope gate without changing HAM classifier weights.

The gate uses frozen penultimate-layer features from the existing HAM ResNet-18.
Its operating point is selected from held-out HAM lesions to target 99% in-scope
acceptance; all final performance is reported on lesion/image-disjoint test data.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset
from torchvision import models as tvm

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
MANIFEST_PATH = BACKEND / "data" / "manifests" / "skin-ood-v1.json"
SPLIT_PATH = BACKEND / "data" / "split.csv"
HAM_ROOT = BACKEND / "data" / "extracted" / "HAM10000" / "ISIC2018-Task3" / "ISIC2018_Task3_Training_Input"
HAM_CHECKPOINT = BACKEND / "models" / "resnet18_best.pth"
MODEL_DIR = BACKEND / "models" / "skin_ood"
REPORT_PATH = BACKEND / "data" / "reports" / "skin_ood_metrics.json"
FEATURE_CACHE = BACKEND / "data" / ".staging" / "skin_ood_features.npy"
FEATURE_CACHE_META = BACKEND / "data" / ".staging" / "skin_ood_features.json"
TARGET_SKIN_ACCEPTANCE = 0.99

sys.path.insert(0, str(BACKEND))
import fusion_utils as fu  # noqa: E402


class ImageDataset(Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(row["path"]) as image:
            tensor = fu.EVAL_TF(image.convert("RGB"))
        return tensor, index


def load_rows():
    split = pd.read_csv(SPLIT_PATH, dtype={"image_id": str, "lesion_id": str})
    ham = []
    for row in split.to_dict("records"):
        split_name = "validation" if row["split"] == "val" else row["split"]
        ham.append({"path": str(HAM_ROOT / f"{row['image_id']}.jpg"),
                    "label": 1, "group": "skin", "split": split_name,
                    "class": row["dx"], "sourceId": row["lesion_id"]})

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    negatives = []
    for row in manifest["openImages"]["records"]:
        if row["status"] != "accepted":
            continue
        negatives.append({"path": str(BACKEND / "data" / "processed" / "skin_ood" / row["path"]),
                          "label": 0, "group": row["group"], "split": row["split"],
                          "class": row["label"], "sourceId": row["imageId"]})

    forms = manifest["symageForms"]
    for row in forms["records"]:
        source_split = row["split"]
        # Preserve Symage's document-disjoint official test set and reserve a
        # deterministic 15% of its training identities for validation.
        identity_bucket = int(hashlib.sha256(str(row["identityId"]).encode()).hexdigest()[:8], 16) % 100
        split_name = ("test" if source_split == "test" else
                      "validation" if identity_bucket < 15 else "train")
        negatives.append({"path": str(BACKEND / "data" / "processed" / "skin_ood" / row["path"]),
                          "label": 0, "group": "forms", "split": split_name,
                          "class": row["formId"], "sourceId": str(row["identityId"])})

    screenshots = manifest["syntheticScreenshots"]
    for row in screenshots["records"]:
        negatives.append({"path": str(BACKEND / "data" / "processed" / "skin_ood" / row["path"]),
                          "label": 0, "group": "screenshots", "split": row["split"],
                          "class": row["templateId"], "sourceId": row["imageId"]})

    for row in ham + negatives:
        if not Path(row["path"]).is_file():
            raise FileNotFoundError(row["path"])
    return ham + negatives


def feature_matrix(rows):
    torch.set_num_threads(min(8, torch.get_num_threads()))
    net = tvm.resnet18(weights=None)
    net.fc = nn.Linear(512, 7)
    state = torch.load(HAM_CHECKPOINT, map_location="cpu", weights_only=True)
    net.load_state_dict(state)
    encoder = nn.Sequential(*list(net.children())[:-1]).eval()
    signature = hashlib.sha256("\n".join(f"{row['path']}|{Path(row['path']).stat().st_size}"
                                            for row in rows).encode()).hexdigest()
    FEATURE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    metadata = {}
    if FEATURE_CACHE_META.is_file():
        try:
            metadata = json.loads(FEATURE_CACHE_META.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metadata = {}
    if metadata.get("signature") == signature and FEATURE_CACHE.is_file():
        vectors = np.lib.format.open_memmap(FEATURE_CACHE, mode="r+")
        start = min(int(metadata.get("completedRows", 0)), len(rows))
        if vectors.shape != (len(rows), 512):
            start = 0
    else:
        vectors = np.lib.format.open_memmap(FEATURE_CACHE, mode="w+", dtype=np.float32,
                                            shape=(len(rows), 512))
        start = 0
        metadata = {"signature": signature, "completedRows": 0, "rows": len(rows)}
    if start == len(rows):
        print(f"Feature extraction: using cached embeddings for all {len(rows)} images", flush=True)
        return np.asarray(vectors)
    loader = DataLoader(ImageDataset(rows), batch_size=64, shuffle=False, num_workers=0)
    started = time.time()
    print(f"Feature extraction: {len(rows)} images, resume at {start}, threads={torch.get_num_threads()}", flush=True)
    with torch.inference_mode():
        for batch, indices in loader:
            first = int(indices[0])
            last = int(indices[-1]) + 1
            if last <= start:
                continue
            outputs = encoder(batch).flatten(1).numpy()
            vectors[indices.numpy()] = outputs
            if last - start >= 640 or last == len(rows):
                vectors.flush()
                metadata["completedRows"] = last
                FEATURE_CACHE_META.write_text(json.dumps(metadata), encoding="utf-8")
                print(f"Feature extraction: {last}/{len(rows)} images ({time.time()-started:.1f}s)", flush=True)
    vectors.flush()
    FEATURE_CACHE_META.write_text(json.dumps({"signature": signature,
                                               "completedRows": len(rows),
                                               "rows": len(rows)}), encoding="utf-8")
    return np.asarray(vectors)


def wilson_interval(successes, total, z=1.959963984540054):
    if not total:
        return None
    p = successes / total
    d = 1 + z * z / total
    center = (p + z * z / (2 * total)) / d
    margin = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return [float(center - margin), float(center + margin)]


def evaluate(rows, scores, threshold):
    y_true = np.array([r["label"] for r in rows], dtype=int)
    y_pred = (scores >= threshold).astype(int)
    result = {
        "sampleCount": len(rows),
        "threshold": float(threshold),
        "skinAcceptance": float((y_pred[y_true == 1] == 1).mean()) if (y_true == 1).any() else None,
        "oodRejection": float((y_pred[y_true == 0] == 0).mean()) if (y_true == 0).any() else None,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balancedAccuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macroF1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "confusionMatrixRowsSkinOodColumnsSkinOod": confusion_matrix(y_true, y_pred, labels=[1, 0]).tolist(),
        "aurocSkinVsOOD": float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) == 2 else None,
        "groups": {},
    }
    for group in sorted({r["group"] for r in rows}):
        indexes = [i for i, row in enumerate(rows) if row["group"] == group]
        actual = y_true[indexes]
        pred = y_pred[indexes]
        group_scores = scores[indexes]
        if group == "skin":
            accepted = int((pred == 1).sum())
            result["groups"][group] = {
                "count": len(indexes), "acceptance": accepted / len(indexes),
                "rejection": 1 - accepted / len(indexes),
                "acceptance95CI": wilson_interval(accepted, len(indexes)),
                "byHAMClass": {},
            }
            for label in sorted({rows[i]["class"] for i in indexes}):
                class_indexes = [i for i in indexes if rows[i]["class"] == label]
                class_accept = sum(y_pred[i] == 1 for i in class_indexes)
                result["groups"][group]["byHAMClass"][label] = {
                    "count": len(class_indexes),
                    "acceptance": class_accept / len(class_indexes),
                    "rejection": 1 - class_accept / len(class_indexes),
                }
        else:
            rejected = int((pred == 0).sum())
            skin_indexes = [i for i, row in enumerate(rows) if row["group"] == "skin"]
            group_auc = roc_auc_score(
                np.r_[np.ones(len(skin_indexes)), np.zeros(len(indexes))],
                np.r_[scores[skin_indexes], group_scores])
            result["groups"][group] = {
                "count": len(indexes), "rejection": rejected / len(indexes),
                "falseAcceptance": 1 - rejected / len(indexes),
                "rejection95CI": wilson_interval(rejected, len(indexes)),
                "aurocSkinVsOOD": float(group_auc),
            }
    return result


def main():
    rows = load_rows()
    features = feature_matrix(rows)
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[row["split"]].append(i)
    train_ids, val_ids, test_ids = (groups[k] for k in ("train", "validation", "test"))
    y = np.array([r["label"] for r in rows], dtype=int)
    x = features
    skin_class_counts = Counter(rows[i]["class"] for i in train_ids if rows[i]["label"] == 1)
    skin_class_count = len(skin_class_counts)
    skin_train_total = sum(skin_class_counts.values())
    sample_weights = np.ones(len(rows), dtype=np.float64)
    for i in train_ids:
        if rows[i]["label"] == 1:
            sample_weights[i] = skin_train_total / (
                skin_class_count * skin_class_counts[rows[i]["class"]])

    candidates = []
    for c in (0.01, 0.1, 1.0, 10.0):
        model = make_pipeline(StandardScaler(), LogisticRegression(
            C=c, class_weight="balanced", max_iter=2000, random_state=4032026,
            solver="liblinear"))
        model.fit(x[train_ids], y[train_ids],
                  standardscaler__sample_weight=sample_weights[train_ids],
                  logisticregression__sample_weight=sample_weights[train_ids])
        scores = model.decision_function(x[val_ids])
        val_y = y[val_ids]
        auc = float(roc_auc_score(val_y, scores))
        candidates.append((auc, c, model))
    _, best_c, classifier = max(candidates, key=lambda item: item[0])

    val_skin_ids = [i for i in val_ids if rows[i]["label"] == 1]
    val_skin_scores = classifier.decision_function(x[val_skin_ids])
    # Calibrate to the target within every HAM class so the dominant nevus
    # class cannot hide worse rejection of rare valid benign classes.
    threshold_by_class = {}
    for label in sorted({rows[i]["class"] for i in val_skin_ids}):
        class_scores = [classifier.decision_function(x[[i]])[0]
                        for i in val_skin_ids if rows[i]["class"] == label]
        threshold_by_class[label] = float(np.quantile(
            class_scores, 1 - TARGET_SKIN_ACCEPTANCE, method="lower"))
    threshold = min(threshold_by_class.values())
    test_scores = classifier.decision_function(x[test_ids])
    test_rows = [rows[i] for i in test_ids]
    val_scores = classifier.decision_function(x[val_ids])
    val_rows = [rows[i] for i in val_ids]
    test_metrics = evaluate(test_rows, test_scores, threshold)
    val_metrics = evaluate(val_rows, val_scores, threshold)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    package = {
        "classifier": classifier,
        "threshold": threshold,
        "hamCheckpointSha256": hashlib.sha256(HAM_CHECKPOINT.read_bytes()).hexdigest(),
        "thresholdPolicy": "Per-HAM-class 1% validation lesion false-rejection target; one global threshold set to the least restrictive class quantile",
        "featureSource": "backend/models/resnet18_best.pth frozen penultimate features (512d)",
        "preprocessing": "backend/fusion_utils.py:EVAL_TF (224x224 RGB, ImageNet mean/std)",
        "trainingPolicy": "HAM positives weighted equally across all seven HAM diagnostic classes",
        "classes": {"1": "HAM10000 skin lesion scope", "0": "known non-skin OOD scope"},
    }
    artifact = MODEL_DIR / "skin_ood_gate.joblib"
    joblib.dump(package, artifact)
    report = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "datasetManifest": str(MANIFEST_PATH.relative_to(REPO)),
        "trainingCounts": {f"{group}/{split}": count for (group, split), count in
                            Counter((rows[i]["group"], rows[i]["split"]) for i in train_ids).items()},
        "validationCounts": {f"{group}/{split}": count for (group, split), count in
                             Counter((rows[i]["group"], rows[i]["split"]) for i in val_ids).items()},
        "testCounts": {f"{group}/{split}": count for (group, split), count in
                       Counter((rows[i]["group"], rows[i]["split"]) for i in test_ids).items()},
        "regularizationCSelectedByValidationAUROC": best_c,
        "validationCandidateAUROC": {str(c): auc for auc, c, _ in candidates},
        "thresholdPolicy": package["thresholdPolicy"],
        "validationThresholdByHAMClass": threshold_by_class,
        "validationMetrics": val_metrics,
        "testMetrics": test_metrics,
        "trainingDevice": "cpu",
        "existingHamCheckpointSha256": hashlib.sha256(HAM_CHECKPOINT.read_bytes()).hexdigest(),
        "gateArtifact": str(artifact.relative_to(REPO)),
        "limitations": [
            "Known OOD test scope is limited to synthetic forms, synthetic website screenshots, and selected Open Images animal/object classes.",
            "These metrics do not establish universal detection of arbitrary or emerging out-of-distribution images.",
            "This gate is a research scope filter and is not a medical diagnostic validation.",
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"validationMetrics": val_metrics, "testMetrics": test_metrics,
                      "gateArtifact": str(artifact), "report": str(REPORT_PATH)}, indent=2))


if __name__ == "__main__":
    main()
