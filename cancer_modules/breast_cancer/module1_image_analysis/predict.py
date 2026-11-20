"""Run validator-gated BUSI ultrasound classification."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image


CLASS_NAMES = ("Normal", "Benign", "Malignant")
VALIDATOR_THRESHOLD = 0.50
CLASSIFICATION_THRESHOLD = 0.60
MODEL_DIR = Path(__file__).resolve().parent
CLASSIFIER_PATH = MODEL_DIR / "busi_mobilenetv2.keras"
VALIDATOR_PATH = MODEL_DIR / "busi_ultrasound_validator.keras"


def _preprocess_image(image_path: Path, size: tuple[int, int]) -> np.ndarray:
    """Load an image as RGB, resize it, and apply MobileNetV2 preprocessing."""
    with Image.open(image_path) as image:
        image = image.convert("RGB").resize(size, Image.Resampling.BILINEAR)
        pixels = np.asarray(image, dtype=np.float32)

    pixels = tf.keras.applications.mobilenet_v2.preprocess_input(pixels)
    return np.expand_dims(pixels, axis=0)


def _valid_probability(output: np.ndarray) -> float:
    """Return the valid-class probability from sigmoid or binary softmax output."""
    values = np.asarray(output, dtype=np.float32).reshape(-1)
    if values.size == 1:
        return float(values[0])
    if values.size == 2:
        # For a two-unit softmax validator, class index 1 is assumed to mean valid.
        return float(values[1])
    raise ValueError(
        "Validator must return one sigmoid probability or two softmax probabilities; "
        f"received {values.size} values."
    )


def predict(image_path: Path) -> None:
    """Validate an ultrasound image, then classify it when it passes validation."""
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    validator = tf.keras.models.load_model(VALIDATOR_PATH)
    classifier = tf.keras.models.load_model(CLASSIFIER_PATH)

    validator_input = _preprocess_image(image_path, (128, 128))
    validator_probability = _valid_probability(
        validator.predict(validator_input, verbose=0)
    )
    print(f"Validator probability: {validator_probability:.4f}")

    if validator_probability < VALIDATOR_THRESHOLD:
        print("Prediction: Invalid image")
        print("Confidence: N/A (rejected by validator)")
        print("Normal probability: N/A")
        print("Benign probability: N/A")
        print("Malignant probability: N/A")
        return

    classifier_input = _preprocess_image(image_path, (224, 224))
    probabilities = np.asarray(
        classifier.predict(classifier_input, verbose=0), dtype=np.float32
    ).reshape(-1)
    if probabilities.size != len(CLASS_NAMES):
        raise ValueError(
            f"Classifier must return 3 probabilities; received {probabilities.size}."
        )

    predicted_index = int(np.argmax(probabilities))
    confidence = float(probabilities[predicted_index])
    prediction = (
        CLASS_NAMES[predicted_index]
        if confidence >= CLASSIFICATION_THRESHOLD
        else "Uncertain"
    )

    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence:.4f}")
    for class_name, probability in zip(CLASS_NAMES, probabilities):
        print(f"{class_name} probability: {float(probability):.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and classify a BUSI breast ultrasound image."
    )
    parser.add_argument("image_path", type=Path, help="Path to an ultrasound image")
    args = parser.parse_args()
    predict(args.image_path)


if __name__ == "__main__":
    main()
