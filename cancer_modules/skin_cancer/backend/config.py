"""Shared backend paths and environment-based runtime configuration."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(BACKEND_DIR / "models"))).expanduser().resolve()
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", str(BACKEND_DIR / "results"))).expanduser().resolve()
REPORTS_DB_PATH = Path(os.getenv("REPORTS_DB_PATH", str(BACKEND_DIR / "reports.sqlite3"))).expanduser().resolve()
DEVICE = os.getenv("MODEL_DEVICE", "cpu")
MAX_IMAGE_BYTES = 10 * 1024 * 1024
FRONTEND_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGIN", "http://localhost:3000,http://127.0.0.1:3000,https://wecure-five.vercel.app"
    ).split(",")
    if origin.strip()
)
