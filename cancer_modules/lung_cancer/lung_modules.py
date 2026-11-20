"""Lung research model adapters for the WeCure prototype.

The image weights are a 2D slice classifier from the reference project. The
clinical model is trained from the included tabular CSV when first requested.
Neither output is a clinical diagnosis.
"""

from functools import lru_cache
import os
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parent
IMAGE_MODEL_PATH = ROOT / "models" / "lung_cancer" / "keras_model.h5"
CLINICAL_DATA_PATH = ROOT / "data" / "lung_cancer" / "clinical.csv"

CLINICAL_FEATURES = [
    "Age",
    "Gender",
    "Air Pollution",
    "Alcohol use",
    "Balanced Diet",
    "Obesity",
    "Smoking",
    "Passive Smoker",
    "Fatigue",
    "Weight Loss",
    "Shortness of Breath",
    "Wheezing",
    "Swallowing Difficulty",
    "Clubbing of Finger Nails",
    "Frequent Cold",
    "Dry Cough",
    "Snoring",
]


@lru_cache(maxsize=1)
def _image_model():
    if not IMAGE_MODEL_PATH.is_file():
        raise FileNotFoundError("Lung image model weights are missing")
    os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
    import tensorflow as tf

    class LegacyDepthwiseConv2D(tf.keras.layers.DepthwiseConv2D):
        @classmethod
        def from_config(cls, config):
            # Older Keras saved this standard layer with groups=1 in H5 config.
            # DepthwiseConv2D already has fixed depthwise grouping semantics.
            config = dict(config)
            config.pop("groups", None)
            return super().from_config(config)

    return tf.keras.models.load_model(
        IMAGE_MODEL_PATH,
        custom_objects={"DepthwiseConv2D": LegacyDepthwiseConv2D},
        compile=False,
    )


def predict_lung_image(image: Image.Image) -> dict:
    """Return the original binary model's normal-vs-cancer slice estimate."""
    model = _image_model()
    resized = image.convert("RGB").resize((224, 224))
    batch = np.asarray(resized, dtype=np.float32)[None, ...] / 255.0
    raw = np.asarray(model.predict(batch, verbose=0)).reshape(-1)
    if raw.size not in (1, 2) or not np.all(np.isfinite(raw)):
        raise ValueError("The image model returned an unsupported output")

    # The reference app's class order is 0=normal, 1=lung cancer; some H5
    # variants return both class scores, while others return only p(normal).
    if raw.size == 2:
        normal_probability, cancer_probability = (float(np.clip(value, 0.0, 1.0)) for value in raw)
        total = normal_probability + cancer_probability
        if total <= 0:
            raise ValueError("The image model returned empty class scores")
        normal_probability /= total
        cancer_probability /= total
    else:
        normal_probability = float(np.clip(raw[0], 0.0, 1.0))
        cancer_probability = 1.0 - normal_probability
    label = "Normal-like slice" if normal_probability >= 0.5 else "Cancer-like slice"
    confidence = max(normal_probability, cancer_probability)
    return {
        "label": label,
        "classification": "normal" if normal_probability >= 0.5 else "cancer",
        "confidence": confidence,
        "probabilities": {
            "normal_like_slice": normal_probability,
            "cancer_like_slice": cancer_probability,
        },
    }


@lru_cache(maxsize=1)
def _clinical_model():
    if not CLINICAL_DATA_PATH.is_file():
        raise FileNotFoundError("Lung clinical CSV is missing")
    data = pd.read_csv(CLINICAL_DATA_PATH)
    required = set(CLINICAL_FEATURES + ["Level"])
    if not required.issubset(data.columns):
        raise ValueError("The included lung clinical CSV has unexpected columns")
    features = data[CLINICAL_FEATURES].apply(pd.to_numeric, errors="raise")
    labels = data["Level"].astype(str)
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42, stratify=labels
    )
    model = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    holdout_accuracy = float(accuracy_score(y_test, model.predict(x_test)))
    return model, holdout_accuracy


def predict_lung_clinical(values: dict[str, float]) -> dict:
    missing = [feature for feature in CLINICAL_FEATURES if feature not in values]
    if missing:
        raise ValueError("Missing clinical fields: " + ", ".join(missing))
    row = pd.DataFrame([{feature: float(values[feature]) for feature in CLINICAL_FEATURES}])
    model, holdout_accuracy = _clinical_model()
    probabilities = model.predict_proba(row)[0]
    class_probabilities = {
        str(label): float(probability)
        for label, probability in zip(model.classes_, probabilities)
    }
    prediction = max(class_probabilities, key=class_probabilities.get)
    return {
        "label": prediction,
        "classification": prediction.lower(),
        "confidence": class_probabilities[prediction],
        "probabilities": class_probabilities,
        "referenceHoldoutAccuracy": holdout_accuracy,
    }
