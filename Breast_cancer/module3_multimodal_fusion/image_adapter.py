"""Structured wrapper for the existing BUSI image prediction models.

This adapter reports image-model evidence only. It does not combine results
with clinical records or produce a diagnosis.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError


CLASS_NAMES = ("Normal", "Benign", "Malignant")
VALIDATOR_THRESHOLD = 0.50
CLASSIFICATION_THRESHOLD = 0.60

MODULE1_DIR = Path(__file__).resolve().parent.parent / "module1_image_analysis"
VALIDATOR_PATH = MODULE1_DIR / "busi_ultrasound_validator.keras"
CLASSIFIER_PATH = MODULE1_DIR / "busi_mobilenetv2.keras"


def _empty_class_probabilities() -> dict[str, float | None]:
    return {class_name: None for class_name in CLASS_NAMES}


def _result(
    *,
    status: str,
    prediction: str | None = None,
    confidence: float | None = None,
    class_probabilities: dict[str, float | None] | None = None,
    validator_probability: float | None = None,
    message: str,
) -> dict[str, Any]:
    """Build a stable result shape for every image-adapter outcome."""
    return {
        "status": status,
        "prediction": prediction,
        "confidence": confidence,
        "class_probabilities": (
            class_probabilities
            if class_probabilities is not None
            else _empty_class_probabilities()
        ),
        "validator_probability": validator_probability,
        "message": message,
    }


class TensorFlowUnavailableError(RuntimeError):
    """Raised internally when TensorFlow cannot be imported in this runtime."""


@lru_cache(maxsize=1)
def _load_models() -> tuple[Any, Any, Any]:
    """Load the existing validator and classifier once per Python process."""
    missing = [str(path) for path in (VALIDATOR_PATH, CLASSIFIER_PATH) if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required Module 1 model file(s) not found: " + ", ".join(missing))

    try:
        import tensorflow as tf
    except Exception as exc:
        raise TensorFlowUnavailableError(
            "TensorFlow could not be imported in this environment. The BUSI image "
            "models cannot run here; use an authorized runtime where TensorFlow "
            "imports successfully. No installation or security-setting changes "
            "were attempted. Original import error: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    try:
        validator = tf.keras.models.load_model(VALIDATOR_PATH)
        classifier = tf.keras.models.load_model(CLASSIFIER_PATH)
    except Exception as exc:
        raise RuntimeError(
            "Could not load the Module 1 Keras model files. Check TensorFlow/Keras "
            "compatibility and that both files are intact. "
            f"Original error: {type(exc).__name__}: {exc}"
        ) from exc
    return tf, validator, classifier


def _preprocess_image(image_path: Path, size: tuple[int, int], tf: Any) -> np.ndarray:
    """Match Module 1: RGB, bilinear resize, then MobileNetV2 preprocessing."""
    with Image.open(image_path) as image:
        image = image.convert("RGB").resize(size, Image.Resampling.BILINEAR)
        pixels = np.asarray(image, dtype=np.float32)

    pixels = tf.keras.applications.mobilenet_v2.preprocess_input(pixels)
    return np.expand_dims(pixels, axis=0)


def _valid_probability(output: Any) -> float:
    """Match Module 1's scalar-sigmoid or two-value softmax interpretation."""
    values = np.asarray(output, dtype=np.float32).reshape(-1)
    if values.size == 1:
        return float(values[0])
    if values.size == 2:
        # Module 1 treats binary softmax class index 1 as the valid class.
        return float(values[1])
    raise ValueError(
        "Validator must return one sigmoid probability or two softmax probabilities; "
        f"received {values.size} values."
    )


def predict_ultrasound(image_path: str | Path) -> dict[str, Any]:
    """Validate and classify an image, returning image evidence as a dictionary.

    The class probabilities describe only the BUSI image classifier. They are
    not combined with Module 2 clinical grade predictions.
    """
    path = Path(image_path).expanduser()
    if not path.is_file():
        return _result(
            status="invalid_image",
            message=f"Image file not found: {path}",
        )

    try:
        tf, validator, classifier = _load_models()
    except FileNotFoundError as exc:
        return _result(status="model_unavailable", message=str(exc))
    except TensorFlowUnavailableError as exc:
        return _result(status="dependency_unavailable", message=str(exc))
    except Exception as exc:
        return _result(status="model_error", message=str(exc))

    try:
        validator_input = _preprocess_image(path, (128, 128), tf)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return _result(
            status="invalid_image",
            message=f"The image could not be opened or decoded: {exc}",
        )

    try:
        validator_probability = _valid_probability(
            validator.predict(validator_input, verbose=0)
        )
    except Exception as exc:
        return _result(
            status="prediction_error",
            message=f"Validator prediction failed: {type(exc).__name__}: {exc}",
        )

    if validator_probability < VALIDATOR_THRESHOLD:
        return _result(
            status="rejected",
            prediction="Invalid image",
            validator_probability=validator_probability,
            message=(
                "The ultrasound validator score is below 0.50. The image was "
                "rejected before class prediction."
            ),
        )

    try:
        classifier_input = _preprocess_image(path, (224, 224), tf)
        probabilities = np.asarray(
            classifier.predict(classifier_input, verbose=0), dtype=np.float32
        ).reshape(-1)
        if probabilities.size != len(CLASS_NAMES):
            raise ValueError(
                f"Classifier must return 3 probabilities; received {probabilities.size}."
            )
        if not np.all(np.isfinite(probabilities)):
            raise ValueError("Classifier returned a non-finite class probability.")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return _result(
            status="prediction_error",
            validator_probability=validator_probability,
            message=f"Classifier input or output was invalid: {exc}",
        )
    except Exception as exc:
        return _result(
            status="prediction_error",
            validator_probability=validator_probability,
            message=f"Classifier prediction failed: {type(exc).__name__}: {exc}",
        )

    predicted_index = int(np.argmax(probabilities))
    confidence = float(probabilities[predicted_index])
    class_probabilities = {
        class_name: float(probability)
        for class_name, probability in zip(CLASS_NAMES, probabilities)
    }

    if confidence < CLASSIFICATION_THRESHOLD:
        return _result(
            status="uncertain",
            prediction="Uncertain",
            confidence=confidence,
            class_probabilities=class_probabilities,
            validator_probability=validator_probability,
            message=(
                "The highest image-class probability is below 0.60, so the "
                "classifier result is marked uncertain."
            ),
        )

    return _result(
        status="success",
        prediction=CLASS_NAMES[predicted_index],
        confidence=confidence,
        class_probabilities=class_probabilities,
        validator_probability=validator_probability,
        message="Image classification completed. This is image-model evidence only.",
    )
