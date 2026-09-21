"""Runtime paths and settings helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.fsutil import write_text_atomic
from app.models import AppSettings

ROOT = Path(os.environ.get("SUITE_ROOT", Path(__file__).resolve().parents[1]))
DATA_DIR = Path(os.environ.get("SUITE_DATA", ROOT / "data"))
LAYOUTS_DIR = Path(os.environ.get("SUITE_LAYOUTS", ROOT / "layouts"))
GALLERY_DIR = Path(os.environ.get("SUITE_GALLERY", DATA_DIR / "gallery"))
CONFIG_PATH = Path(os.environ.get("SUITE_CONFIG", DATA_DIR / "config.json"))
CATALOG_PATH = Path(os.environ.get("SUITE_CATALOG", DATA_DIR / "catalog.json"))

# GET /api/settings never returns live provider keys. POST treats this sentinel
# (or a blank field) as "keep the stored key"; a new non-blank value replaces it.
REDACTED_API_KEY = "********"
_PROVIDER_SECTIONS = ("jellyfin", "jellyseerr", "tmdb", "omdb")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> AppSettings:
    ensure_dirs()
    if CONFIG_PATH.is_file():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return AppSettings.model_validate(data)
        except (OSError, json.JSONDecodeError, ValueError):
            # Leave the broken file on disk so the operator can repair it;
            # do not overwrite with defaults.
            return AppSettings()
    settings = AppSettings()
    save_settings(settings)
    return settings


def save_settings(settings: AppSettings) -> None:
    ensure_dirs()
    write_text_atomic(CONFIG_PATH, settings.model_dump_json(indent=2))


def is_redacted_api_key(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and set(text) <= {"*"} and len(text) >= 4


def redact_settings_dump(data: dict) -> dict:
    """Copy of a settings dict with provider api_keys replaced by a sentinel."""
    out = dict(data or {})
    for section in _PROVIDER_SECTIONS:
        block = dict(out.get(section) or {})
        if block.get("api_key"):
            block["api_key"] = REDACTED_API_KEY
            out[section] = block
    return out


def merge_provider_secrets(incoming: AppSettings, stored: AppSettings) -> AppSettings:
    """Keep stored provider keys when the POST sends a blank or redacted value."""
    payload = incoming.model_dump()
    stored_dump = stored.model_dump()
    for section in _PROVIDER_SECTIONS:
        block = dict(payload.get(section) or {})
        previous = (stored_dump.get(section) or {}).get("api_key") or ""
        key = block.get("api_key")
        if is_redacted_api_key(key) or key is None:
            block["api_key"] = previous
            payload[section] = block
    return AppSettings.model_validate(payload)


def public_base_url(settings: AppSettings | None = None) -> str:
    env = os.environ.get("PUBLIC_BASE_URL")
    if env:
        return env.rstrip("/")
    current = settings or load_settings()
    return (current.public_base_url or "http://127.0.0.1:8787").rstrip("/")
