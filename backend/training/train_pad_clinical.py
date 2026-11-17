"""Train and evaluate the PAD-UFES-20 clinical-only model."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader, TensorDataset


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.models.pad_clinical_model import PADClinicalMLP
from backend.preprocessing.pad_clinical_preprocessing import (
    CLINICAL_FEATURES,
    build_lesion_table,
    create_clinical_preprocessor,
    get_split_data,
)


BACKEND = PROJECT_ROOT / "backend"
DATASET_CSV = (
    BACKEND / "data" / "processed" / "PAD-UFES-20" / "v1"
    / "matched_images.csv"
)

OUTPUT_DIR = BACKEND / "models" / "pad_ufes20"
RESULTS_DIR = BACKEND / "results" / "pad_ufes20"

MODEL_PATH = OUTPUT_DIR / "clinical_best.pth"
PREPROCESSOR_PATH = OUTPUT_DIR / "clinical_preprocessor.joblib"
LABELS_PATH = OUTPUT_DIR / "clinical_labels.json"

SEED = 42
BATCH_SIZE = 32
EPOCHS = 200
LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0001
PATIENCE = 20


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def make_loader(
    features: np.ndarray,
    labels: np.ndarray,
    shuffle: bool,
) -> DataLoader:
    dataset = TensorDataset(
        torch.tensor(features, dtype=torch.float32),
        torch.tensor(labels, dtype=torch.long),
    )

    return DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=shuffle,
        drop_last=False,
    )


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    all_predictions = []
    all_targets = []

    with torch.no_grad():
        for features, targets in loader:
            features = features.to(device)
            logits = model(features)

            predictions = torch.argmax(logits, dim=1)

            all_predictions.extend(predictions.cpu().numpy())
            all_targets.extend(targets.numpy())

    return (
        np.asarray(all_targets, dtype=np.int64),
        np.asarray(all_predictions, dtype=np.int64),
    )


def main() -> None:
    set_seed()

    if not DATASET_CSV.is_file():
        raise FileNotFoundError(
            f"Processed PAD-UFES-20 CSV not found: {DATASET_CSV}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n========== PAD-UFES-20 CLINICAL TRAINING ==========")

    # 1. Build a separate lesion-level dataset.
    lesions_path = (
        BACKEND / "data" / "processed" / "PAD-UFES-20" / "v1"
        / "clinical_lesions.csv"
    )

    lesions = build_lesion_table(
        matched_csv=DATASET_CSV,
        output_csv=lesions_path,
    )

    train_df, val_df, test_df = get_split_data(lesions)

    print(f"Unique lesions: {len(lesions)}")
    print(f"Train lesions: {len(train_df)}")
    print(f"Validation lesions: {len(val_df)}")
    print(f"Test lesions: {len(test_df)}")

    # 2. Create a fixed label mapping.
    classes = sorted(lesions["diagnostic"].unique().tolist())

    if len(classes) != 6:
        raise ValueError(
            f"Expected six PAD-UFES-20 classes, found {classes}"
        )

    label_to_index = {
        label: index for index, label in enumerate(classes)
    }

    index_to_label = {
        index: label for label, index in label_to_index.items()
    }

    for split_name, frame in (
        ("train", train_df),
        ("validation", val_df),
        ("test", test_df),
    ):
        missing_classes = set(classes) - set(frame["diagnostic"].unique())

        if missing_classes:
            raise ValueError(
                f"{split_name} split is missing classes: "
                f"{sorted(missing_classes)}. "
                "Do not silently change the patient-level split."
            )

    y_train = train_df["diagnostic"].map(label_to_index).to_numpy(
        dtype=np.int64
    )
    y_val = val_df["diagnostic"].map(label_to_index).to_numpy(
        dtype=np.int64
    )
    y_test = test_df["diagnostic"].map(label_to_index).to_numpy(
        dtype=np.int64
    )

    # 3. Fit preprocessing ONLY on training features.
    preprocessor = create_clinical_preprocessor()

    X_train = preprocessor.fit_transform(
        train_df[CLINICAL_FEATURES]
    ).astype(np.float32)

    X_val = preprocessor.transform(
        val_df[CLINICAL_FEATURES]
    ).astype(np.float32)

    X_test = preprocessor.transform(
        test_df[CLINICAL_FEATURES]
    ).astype(np.float32)

    if not (
        np.isfinite(X_train).all()
        and np.isfinite(X_val).all()
        and np.isfinite(X_test).all()
    ):
        raise ValueError("Non-finite values found after preprocessing.")

    input_features = X_train.shape[1]
    print(f"Clinical input features after encoding: {input_features}")

    # 4. Calculate class weights from training labels only.
    class_weights = compute_class_weight(
        class_weight="balanced",
        classes=np.arange(len(classes)),
        y=y_train,
    )

    weights_tensor = torch.tensor(
        class_weights,
        dtype=torch.float32,
    )

    # 5. Prepare loaders and model.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training device: {device}")

    train_loader = make_loader(X_train, y_train, shuffle=True)
    val_loader = make_loader(X_val, y_val, shuffle=False)
    test_loader = make_loader(X_test, y_test, shuffle=False)

    model = PADClinicalMLP(
        input_features=input_features,
        num_classes=len(classes),
    ).to(device)

    criterion = nn.CrossEntropyLoss(
        weight=weights_tensor.to(device)
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )

    # 6. Train with validation Macro-F1 early stopping.
    best_val_f1 = -1.0
    best_epoch = 0
    epochs_without_improvement = 0
    history = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        running_loss = 0.0
        total_samples = 0

        for features, targets in train_loader:
            features = features.to(device)
            targets = targets.to(device)

            optimizer.zero_grad(set_to_none=True)

            logits = model(features)
            loss = criterion(logits, targets)

            loss.backward()
            optimizer.step()

            running_loss += loss.item() * len(targets)
            total_samples += len(targets)

        train_loss = running_loss / max(total_samples, 1)

        val_targets, val_predictions = evaluate(
            model, val_loader, device
        )

        val_macro_f1 = f1_score(
            val_targets,
            val_predictions,
            labels=np.arange(len(classes)),
            average="macro",
            zero_division=0,
        )

        val_accuracy = accuracy_score(
            val_targets,
            val_predictions,
        )

        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "validation_macro_f1": float(val_macro_f1),
            "validation_accuracy": float(val_accuracy),
        })

        if val_macro_f1 > best_val_f1:
            best_val_f1 = float(val_macro_f1)
            best_epoch = epoch
            epochs_without_improvement = 0

            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "input_features": input_features,
                    "num_classes": len(classes),
                    "classes": classes,
                    "best_epoch": best_epoch,
                    "validation_macro_f1": best_val_f1,
                    "seed": SEED,
                },
                MODEL_PATH,
            )

        else:
            epochs_without_improvement += 1

        if epoch == 1 or epoch % 10 == 0:
            print(
                f"Epoch {epoch:03d}/{EPOCHS} | "
                f"Loss: {train_loss:.4f} | "
                f"Val Macro-F1: {val_macro_f1:.4f} | "
                f"Val Accuracy: {val_accuracy:.4f}"
            )

        if epochs_without_improvement >= PATIENCE:
            print(f"Early stopping at epoch {epoch}.")
            break

    # 7. Load the best validation checkpoint.
    checkpoint = torch.load(
        MODEL_PATH,
        map_location=device,
        weights_only=True,
    )

    model.load_state_dict(checkpoint["model_state_dict"])

    # 8. Evaluate the test set ONCE after model selection.
    test_targets, test_predictions = evaluate(
        model, test_loader, device
    )

    report = classification_report(
        test_targets,
        test_predictions,
        labels=np.arange(len(classes)),
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        test_targets,
        test_predictions,
        labels=np.arange(len(classes)),
    )

    metrics = {
        "dataset": "PAD-UFES-20",
        "task": "clinical-only six-class classification",
        "clinical_features": CLINICAL_FEATURES,
        "classes": classes,
        "input_features_after_encoding": int(input_features),
        "lesion_counts": {
            "total": int(len(lesions)),
            "train": int(len(train_df)),
            "validation": int(len(val_df)),
            "test": int(len(test_df)),
        },
        "best_epoch": int(best_epoch),
        "best_validation_macro_f1": float(best_val_f1),
        "test_accuracy": float(accuracy_score(
            test_targets, test_predictions
        )),
        "test_balanced_accuracy": float(balanced_accuracy_score(
            test_targets, test_predictions
        )),
        "test_macro_f1": float(f1_score(
            test_targets,
            test_predictions,
            average="macro",
            zero_division=0,
        )),
        "test_weighted_f1": float(f1_score(
            test_targets,
            test_predictions,
            average="weighted",
            zero_division=0,
        )),
        "test_classification_report": report,
        "test_confusion_matrix": matrix.tolist(),
        "test_class_support": {
            label: int((test_targets == index).sum())
            for index, label in index_to_label.items()
        },
        "warning": (
            "Small test support for some classes may make class-specific "
            "metrics unstable. This is an academic research model, not "
            "a clinical diagnostic system."
        ),
    }

    # 9. Save PAD-specific artifacts only.
    joblib.dump(preprocessor, PREPROCESSOR_PATH)

    LABELS_PATH.write_text(
        json.dumps(index_to_label, indent=2),
        encoding="utf-8",
    )

    (RESULTS_DIR / "clinical_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    pd.DataFrame(
        matrix,
        index=classes,
        columns=classes,
    ).to_csv(RESULTS_DIR / "clinical_confusion_matrix.csv")

    pd.DataFrame(history).to_csv(
        RESULTS_DIR / "clinical_training_history.csv",
        index=False,
    )

    print("\n========== FINAL TEST RESULTS ==========")
    print(f"Best epoch: {best_epoch}")
    print(f"Test accuracy: {metrics['test_accuracy']:.4f}")
    print(f"Test balanced accuracy: {metrics['test_balanced_accuracy']:.4f}")
    print(f"Test macro-F1: {metrics['test_macro_f1']:.4f}")
    print(f"Test weighted-F1: {metrics['test_weighted_f1']:.4f}")

    print("\nClass-wise test support:")
    for label, support in metrics["test_class_support"].items():
        print(f"{label}: {support}")

    print("\nArtifacts saved:")
    print(MODEL_PATH)
    print(PREPROCESSOR_PATH)
    print(LABELS_PATH)
    print(RESULTS_DIR)

    print(
        "\nResearch/educational model only. "
        "Not intended for medical diagnosis or treatment decisions."
    )


if __name__ == "__main__":
    main()
