"""Train and evaluate patient-level MRI-only, clinical-only and fused IDH models."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
from pathlib import Path

import joblib
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / "reports" / ".mplconfig"))
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageFile
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, classification_report,
                             confusion_matrix, f1_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, Dataset

from cancers.brain.multimodal.config import (ARTIFACT_DIR, BATCH_SIZE, CLASSES,
    CLINICAL_FILE, DATA_ROOT, EPOCHS, IMAGE_SIZE, MAX_SLICES_PER_PATIENT,
    PATIENCE, PRETRAINED_CHECKPOINT, REPORT_DIR, SEED)
from cancers.brain.multimodal.dataset import load_paired_patients
from cancers.brain.multimodal.models import (ClinicalMLP, FusionModel, MRIHead,
    build_pretrained_effnet)
from cancers.brain.multimodal.preprocessing import (clinical_frame,
    make_clinical_preprocessor, select_slice_paths, MRI_IMAGE_TRANSFORM)

ImageFile.LOAD_TRUNCATED_IMAGES = False
def set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


class SliceDataset(Dataset):
    def __init__(self, paths: list[str]): self.paths = paths
    def __len__(self): return len(self.paths)
    def __getitem__(self, index):
        path = self.paths[index]
        try:
            with Image.open(path) as im:
                image = im.convert("L").convert("RGB")
                return MRI_IMAGE_TRANSFORM(image)
        except Exception as exc:
            raise RuntimeError(f"Cannot decode MRI slice {path}: {exc}") from exc


def extract_patient_features(frame: pd.DataFrame, checkpoint: Path, device: torch.device,
                             cache_dir: Path, force: bool = False) -> np.ndarray:
    digest_source = "|".join(f"{r.patient_id}:{','.join(select_slice_paths(r.slice_paths, MAX_SLICES_PER_PATIENT))}" for r in frame.itertuples())
    checkpoint_stat = checkpoint.stat()
    digest = hashlib.sha256(f"{digest_source}|{checkpoint_stat.st_size}|{checkpoint_stat.st_mtime_ns}|{MAX_SLICES_PER_PATIENT}".encode()).hexdigest()[:20]
    cache_path = cache_dir / f"mri_patient_features_{digest}.npz"
    if cache_path.is_file() and not force:
        print(f"Loading cached frozen EfficientNet embeddings: {cache_path}", flush=True)
        data = np.load(cache_path)
        if data["patient_ids"].tolist() == frame.patient_id.tolist(): return data["features"].astype(np.float32)
    encoder = build_pretrained_effnet(str(checkpoint), device)
    all_paths, groups = [], []
    for row_idx, row in enumerate(frame.itertuples()):
        paths = select_slice_paths(row.slice_paths, MAX_SLICES_PER_PATIENT)
        all_paths.extend(paths); groups.extend([row_idx] * len(paths))
    loader = DataLoader(SliceDataset(all_paths), batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    slice_features = []
    encoder.eval()
    with torch.inference_mode():
        for batch_index, batch in enumerate(loader, start=1):
            slice_features.append(encoder(batch.to(device)).cpu().numpy())
            if batch_index == 1 or batch_index % 10 == 0 or batch_index == len(loader):
                print(f"Extracting T1CE embeddings: batch {batch_index}/{len(loader)}", flush=True)
    slice_features = np.concatenate(slice_features, axis=0)
    patient_features = np.zeros((len(frame), slice_features.shape[1]), dtype=np.float32)
    group_counts = np.zeros(len(frame), dtype=np.int32)
    for i, group in enumerate(groups):
        patient_features[group] += slice_features[i]
        group_counts[group] += 1
    patient_features /= group_counts[:, None]
    np.savez_compressed(cache_path, patient_ids=np.asarray(frame.patient_id), features=patient_features)
    print(f"Cached {len(frame)} patient representations at {cache_path}", flush=True)
    return patient_features


def split_patients(frame: pd.DataFrame, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    indices = np.arange(len(frame)); labels = frame.label.to_numpy()
    train_val, test = train_test_split(indices, test_size=0.15, random_state=seed, stratify=labels)
    train, val = train_test_split(train_val, test_size=0.15 / 0.85, random_state=seed, stratify=labels[train_val])
    return train, val, test


def build_model(kind: str, clinical_dim: int, mri_dim: int) -> nn.Module:
    if kind == "clinical": return ClinicalMLP(clinical_dim)
    if kind == "mri": return MRIHead(mri_dim)
    return FusionModel(clinical_dim, mri_dim)


def predict(model: nn.Module, kind: str, mri: torch.Tensor, clinical: torch.Tensor,
            indices: np.ndarray, device: torch.device) -> np.ndarray:
    model.eval(); outputs = []
    with torch.no_grad():
        for start in range(0, len(indices), 64):
            ix = indices[start:start + 64]
            if kind == "mri": logits = model(mri[ix].to(device))
            elif kind == "clinical": logits = model(clinical[ix].to(device))
            else: logits = model(mri[ix].to(device), clinical[ix].to(device))
            outputs.append(torch.softmax(logits, dim=1).cpu().numpy())
    return np.concatenate(outputs)


def train_one(kind: str, frame: pd.DataFrame, mri: torch.Tensor, clinical: torch.Tensor,
              train_ix: np.ndarray, val_ix: np.ndarray, device: torch.device,
              artifacts: Path, epochs: int, patience: int) -> tuple[nn.Module, dict]:
    set_seed(SEED)
    model = build_model(kind, clinical.shape[1], mri.shape[1]).to(device)
    counts = np.bincount(frame.label.to_numpy()[train_ix], minlength=2)
    weights = len(train_ix) / (2.0 * np.maximum(counts, 1))
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32, device=device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
    best_score, best_loss, stale, best_epoch = -1.0, float("inf"), 0, 0
    checkpoint_path = artifacts / f"brain_idh_{kind}_best.pt"
    history = []
    for epoch in range(1, epochs + 1):
        started = time.time(); model.train(); shuffled = np.random.permutation(train_ix); losses = []
        for start in range(0, len(shuffled), 32):
            ix = shuffled[start:start + 32]
            mt, ct = mri[ix].to(device), clinical[ix].to(device)
            y = torch.tensor(frame.label.to_numpy()[ix], dtype=torch.long, device=device)
            optimizer.zero_grad(set_to_none=True)
            if kind == "mri": logits = model(mt)
            elif kind == "clinical": logits = model(ct)
            else: logits = model(mt, ct)
            loss = criterion(logits, y); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step(); losses.append(float(loss.detach().cpu()))
        val_probs = predict(model, kind, mri, clinical, val_ix, device)
        val_labels = frame.label.to_numpy()[val_ix]
        val_pred = val_probs.argmax(axis=1)
        val_f1 = f1_score(val_labels, val_pred, average="macro", zero_division=0)
        model.eval()
        with torch.no_grad():
            vi = torch.tensor(val_ix, device=device)
            logits = model(mri[vi]) if kind == "mri" else model(clinical[vi]) if kind == "clinical" else model(mri[vi], clinical[vi])
            val_loss = float(criterion(logits, torch.tensor(val_labels, dtype=torch.long, device=device)).cpu())
        history.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "validation_loss": val_loss, "validation_macro_f1": float(val_f1)})
        print(f"[{kind}] epoch {epoch:02d}/{epochs} train_loss={np.mean(losses):.4f} val_loss={val_loss:.4f} val_macro_f1={val_f1:.4f} ({time.time()-started:.1f}s)", flush=True)
        improved = val_f1 > best_score or (np.isclose(val_f1, best_score) and val_loss < best_loss)
        if improved:
            best_score, best_loss, best_epoch, stale = val_f1, val_loss, epoch, 0
            torch.save({"model_kind": kind, "state_dict": model.state_dict(), "clinical_dim": clinical.shape[1], "mri_dim": mri.shape[1], "classes": CLASSES, "epoch": epoch, "validation_macro_f1": best_score, "seed": SEED}, checkpoint_path)
        else:
            stale += 1
            if stale >= patience: print(f"[{kind}] early stopping at epoch {epoch}", flush=True); break
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["state_dict"]); model.eval()
    return model, {"checkpoint": str(checkpoint_path), "best_epoch": best_epoch, "best_validation_macro_f1": best_score, "history": history}


def score_model(labels: np.ndarray, probabilities: np.ndarray) -> dict:
    pred = probabilities.argmax(axis=1)
    try: auc = float(roc_auc_score(labels, probabilities[:, 1])) if len(np.unique(labels)) == 2 else None
    except ValueError: auc = None
    return {
        "macro_f1": float(f1_score(labels, pred, average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(labels, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, pred)),
        "roc_auc_mutated_positive": auc,
        "per_class": classification_report(labels, pred, labels=[0, 1], target_names=CLASSES, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(labels, pred, labels=[0, 1]).tolist(),
        "n_test_patients": int(len(labels)),
    }


def write_reports(results: dict, labels: np.ndarray, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"model": key, **{m: val[m] for m in ("macro_f1", "accuracy", "balanced_accuracy", "roc_auc_mutated_positive")}} for key, val in results.items()]
    pd.DataFrame(rows).to_csv(report_dir / "model_comparison.csv", index=False)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (key, val) in zip(axes, results.items()):
        cm = np.asarray(val["confusion_matrix"])
        ax.imshow(cm, cmap="Blues"); ax.set_title(key.replace("_", " ").title())
        ax.set_xticks([0, 1], ["Wild type", "Mutated"]); ax.set_yticks([0, 1], ["Wild type", "Mutated"])
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
        for i in range(2):
            for j in range(2): ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="black")
    fig.tight_layout(); fig.savefig(report_dir / "confusion_matrices.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    metrics = ["macro_f1", "balanced_accuracy", "accuracy"]
    x = np.arange(len(results)); width = 0.24
    for j, metric in enumerate(metrics): ax.bar(x + (j - 1) * width, [v[metric] for v in results.values()], width, label=metric.replace("_", " "))
    ax.set_xticks(x, [k.replace("_", " ").title() for k in results]); ax.set_ylim(0, 1); ax.legend(); ax.set_ylabel("Held-out score")
    fig.tight_layout(); fig.savefig(report_dir / "model_comparison.png", dpi=160); plt.close(fig)


def run(data_root: Path = DATA_ROOT, clinical_file: Path = CLINICAL_FILE,
        pretrained_checkpoint: Path = PRETRAINED_CHECKPOINT, epochs: int = EPOCHS,
        patience: int = PATIENCE, force_features: bool = False) -> dict:
    set_seed(SEED); ARTIFACT_DIR.mkdir(parents=True, exist_ok=True); REPORT_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}; patient-level seed={SEED}; slices/patient={MAX_SLICES_PER_PATIENT}", flush=True)
    if not pretrained_checkpoint.is_file(): raise FileNotFoundError(f"Pretrained EfficientNet checkpoint not found: {pretrained_checkpoint}")
    patients, data_report = load_paired_patients(data_root, clinical_file)
    print(f"Paired labeled patients: {len(patients)}; IDH distribution: {data_report['idh_class_counts']}; valid T1CE slices: {data_report['total_valid_t1ce_slices']}", flush=True)
    train_ix, val_ix, test_ix = split_patients(patients, SEED)
    split_report = {"train": patients.patient_id.iloc[train_ix].tolist(), "validation": patients.patient_id.iloc[val_ix].tolist(), "test": patients.patient_id.iloc[test_ix].tolist()}
    if set(split_report["train"]) & set(split_report["validation"]) or set(split_report["train"]) & set(split_report["test"]) or set(split_report["validation"]) & set(split_report["test"]):
        raise RuntimeError("Patient overlap detected across train, validation and test sets")
    print(f"Patient split: train={len(train_ix)}, validation={len(val_ix)}, test={len(test_ix)}; no overlap", flush=True)
    cache_dir = ARTIFACT_DIR / "cache"; cache_dir.mkdir(parents=True, exist_ok=True)
    mri_np = extract_patient_features(patients, pretrained_checkpoint, device, cache_dir, force_features)
    preprocessor = make_clinical_preprocessor()
    clinical_values = clinical_frame(patients)
    clinical_train = preprocessor.fit_transform(clinical_values.iloc[train_ix]).astype(np.float32)
    clinical_all = np.zeros((len(patients), clinical_train.shape[1]), dtype=np.float32)
    clinical_all[train_ix] = clinical_train
    clinical_all[val_ix] = preprocessor.transform(clinical_values.iloc[val_ix]).astype(np.float32)
    clinical_all[test_ix] = preprocessor.transform(clinical_values.iloc[test_ix]).astype(np.float32)
    joblib.dump(preprocessor, ARTIFACT_DIR / "brain_idh_clinical_preprocessor.joblib")
    mri = torch.from_numpy(mri_np); clinical = torch.from_numpy(clinical_all)
    models_meta, models = {}, {}
    for kind in ("mri", "clinical", "fusion"):
        models[kind], models_meta[kind] = train_one(kind, patients, mri, clinical, train_ix, val_ix, device, ARTIFACT_DIR, epochs, patience)
    # Test labels are accessed only after all model selection/checkpointing is complete.
    test_labels = patients.label.to_numpy()[test_ix]
    results = {kind: score_model(test_labels, predict(model, kind, mri, clinical, test_ix, device)) for kind, model in models.items()}
    write_reports(results, test_labels, REPORT_DIR)
    pd.DataFrame(split_report.items(), columns=["split", "patient_ids"]).to_json(REPORT_DIR / "patient_splits.json", orient="records", indent=2)
    summary = {
        "task": "patient-level IDH mutation status (wild type vs mutated)",
        "device": str(device), "seed": SEED, "image_modality": "brain_t1ce", "slices_per_patient": MAX_SLICES_PER_PATIENT,
        "pretrained_image_checkpoint": str(pretrained_checkpoint), "image_encoder": "Frozen EfficientNet-B0; patient representation is mean of evenly sampled slice embeddings",
        "clinical_features": ["Age at Imaging", "Sex at birth", "Tumor Grade", "1p19Q CODEL", "MGMT"],
        "excluded_clinical_columns": {"IDH": "target", "IDH_Testing Method": "direct target leakage", "Subject ID": "identifier only", "Tumor Type": "target-derived/pathology-associated feature excluded"},
        "data": data_report,
        "split_counts": {"train": len(train_ix), "validation": len(val_ix), "test": len(test_ix)},
        "class_counts_by_split": {name: {label: int((patients.label.iloc[ix] == i).sum()) for i, label in enumerate(CLASSES)} for name, ix in [("train", train_ix), ("validation", val_ix), ("test", test_ix)]},
        "patient_overlap": False, "models": models_meta, "test_results": results,
        "limitations": ["Single-source UTSW cohort; no external validation.", "Frozen MRI embeddings are transfer features from the existing four-class MIND EfficientNet checkpoint, not a jointly fine-tuned MRI encoder.", "Clinical preprocessing is fit only on training patients; MRI encoder is frozen and has no access to labels in this experiment."],
    }
    out = REPORT_DIR / "brain_idh_multimodal_metrics.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nHeld-out test metrics", flush=True)
    print(pd.DataFrame([{k: v for k, v in {"model": name, **{m: result[m] for m in ("macro_f1", "accuracy", "balanced_accuracy", "roc_auc_mutated_positive")}}.items()} for name, result in results.items()]).to_string(index=False), flush=True)
    print(f"Metrics: {out}\nComparison: {REPORT_DIR / 'model_comparison.csv'}\nPlots: {REPORT_DIR / 'confusion_matrices.png'}, {REPORT_DIR / 'model_comparison.png'}", flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--clinical-file", type=Path, default=CLINICAL_FILE)
    parser.add_argument("--pretrained-checkpoint", type=Path, default=PRETRAINED_CHECKPOINT)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--patience", type=int, default=PATIENCE)
    parser.add_argument("--force-features", action="store_true")
    args = parser.parse_args()
    run(args.data_root, args.clinical_file, args.pretrained_checkpoint, args.epochs, args.patience, args.force_features)
