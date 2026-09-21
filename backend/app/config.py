"""Runtime paths and settings helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.models import AppSettings

ROOT = Path(os.environ.get("SUITE_ROOT", Path(__file__).resolve().parents[1]))
DATA_DIR = Path(os.environ.get("SUITE_DATA", ROOT / "data"))
LAYOUTS_DIR = Path(os.environ.get("SUITE_LAYOUTS", ROOT / "layouts"))
GALLERY_DIR = Path(os.environ.get("SUITE_GALLERY", DATA_DIR / "gallery"))
CONFIG_PATH = Path(os.environ.get("SUITE_CONFIG", DATA_DIR / "config.json"))
CATALOG_PATH = Path(os.environ.get("SUITE_CATALOG", DATA_DIR / "catalog.json"))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> AppSettings:
    ensure_dirs()
    if CONFIG_PATH.is_file():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return AppSettings.model_validate(data)
    settings = AppSettings()
    save_settings(settings)
    return settings


def save_settings(settings: AppSettings) -> None:
    ensure_dirs()
    CONFIG_PATH.write_text(settings.model_dump_json(indent=2), encoding="utf-8")


def public_base_url(settings: AppSettings | None = None) -> str:
    env = os.environ.get("PUBLIC_BASE_URL")
    if env:
        return env.rstrip("/")
    current = settings or load_settings()
    return (current.public_base_url or "http://127.0.0.1:8787").rstrip("/")
