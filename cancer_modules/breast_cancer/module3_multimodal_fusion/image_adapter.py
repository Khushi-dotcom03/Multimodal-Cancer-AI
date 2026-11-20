"""Structured wrapper for the existing BUSI image prediction models.

This adapter reports image-model evidence only. It does not combine results
with clinical records or produce a diagnosis.
"""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import logging
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError


CLASS_NAMES = ("Normal", "Benign", "Malignant")
VALIDATOR_THRESHOLD = 0.50
CLASSIFICATION_THRESHOLD = 0.60
logger = logging.getLogger(__name__)

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


def _has_bilateral_thoracic_pattern(image_path: Path) -> bool:
    """Catch a conservative, obvious chest-CT pattern before BUSI inference.

    The BUSI validator was trained against CIFAR-10 negatives and can accept
    unrelated medical scans. This narrow guard looks for two large, similarly
    sized dark lung fields in the upper central area of an axial chest image.
    It is intentionally not treated as a general-purpose modality classifier.
    """
    with Image.open(image_path) as image:
        gray = np.asarray(
            image.convert("L").resize((128, 128), Image.Resampling.BILINEAR),
            dtype=np.uint8,
        )[10:118, 10:118]

    dark = gray < 50
    visited = np.zeros(dark.shape, dtype=np.bool_)
    height, width = dark.shape
    left_fields: list[tuple[int, float, float, float, float]] = []
    right_fields: list[tuple[int, float, float, float, float]] = []

    for start_y, start_x in np.argwhere(dark):
        start_y, start_x = int(start_y), int(start_x)
        if visited[start_y, start_x]:
            continue

        visited[start_y, start_x] = True
        pending = deque([(start_y, start_x)])
        area = 0
        min_x = max_x = start_x
        min_y = max_y = start_y
        while pending:
            y, x = pending.pop()
            area += 1
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
            for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and dark[next_y, next_x]
                    and not visited[next_y, next_x]
                ):
                    visited[next_y, next_x] = True
                    pending.append((next_y, next_x))

        box_width = max_x - min_x + 1
        box_height = max_y - min_y + 1
        if area < 350 or box_width < 22 or box_height < 22:
            continue

        center_x = (min_x + max_x + 1) / (2 * width)
        center_y = (min_y + max_y + 1) / (2 * height)
        field = (area, center_x, center_y, box_width / width, box_height / height)
        if 0.20 < center_x < 0.48 and 0.25 < center_y < 0.52:
            left_fields.append(field)
        elif 0.52 < center_x < 0.80 and 0.25 < center_y < 0.52:
            right_fields.append(field)

    for left in left_fields:
        for right in right_fields:
            area_ratio = min(left[0], right[0]) / max(left[0], right[0])
            if (
                area_ratio > 0.40
                and abs(left[1] + right[1] - 1.0) < 0.20
                and abs(left[2] - right[2]) < 0.15
                and min(left[3], right[3]) >= 0.20
                and min(left[4], right[4]) >= 0.20
            ):
                return True
    return False


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
        if _has_bilateral_thoracic_pattern(path):
            return _result(
                status="rejected",
                prediction="Invalid image",
                message=(
                    "Invalid image: This appears to be a chest CT, but Breast Image "
                    "Analysis accepts breast ultrasound images only. The BUSI breast "
                    "classifier was not run."
                ),
            )
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return _result(
            status="invalid_image",
            message=f"The image could not be opened or decoded: {exc}",
        )

    try:
        tf, validator, classifier = _load_models()
    except FileNotFoundError as exc:
        return _result(status="model_unavailable", message=str(exc))
    except TensorFlowUnavailableError as exc:
        return _result(status="dependency_unavailable", message=str(exc))
    except Exception as exc:
        logger.exception("Could not load Module 1 Keras models")
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
