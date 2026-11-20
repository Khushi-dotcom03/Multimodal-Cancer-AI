"""Configuration-driven cancer model registry; never falls back across cancers."""

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / "configurations"


def get_cancer(cancer_type: str) -> dict | None:
    if not cancer_type or any(ch not in "abcdefghijklmnopqrstuvwxyz-" for ch in cancer_type):
        return None
    path = CONFIG_DIR / f"{cancer_type}.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return config if config.get("id") == cancer_type else None


def list_cancers() -> list[dict]:
    return sorted(
        [config for path in CONFIG_DIR.glob("*.json") if (config := _load(path))],
        key=lambda config: config["id"],
    )


def _load(path: Path) -> dict | None:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return config if isinstance(config, dict) and config.get("id") == path.stem else None
