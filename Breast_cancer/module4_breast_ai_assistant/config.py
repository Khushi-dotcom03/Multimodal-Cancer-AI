"""Environment-backed configuration for the independent Module 4 API."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"), override=False)

DEFAULT_MODEL = "openai/gpt-oss-20b"


def get_groq_api_key() -> str | None:
    key = os.getenv("GROQ_API_KEY", "").strip()
    return key or None


def get_groq_model() -> str:
    return os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
