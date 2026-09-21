"""Lightweight ops snapshot (last cron, last generate) for the dashboard."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()


def _path() -> Path:
    from app.config import DATA_DIR, ensure_dirs

    ensure_dirs()
    return DATA_DIR / "ops.json"


def _load_unlocked() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_ops() -> dict[str, Any]:
    with _LOCK:
        return _load_unlocked()


def record_event(kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    from app.fsutil import write_text_atomic

    with _LOCK:
        data = _load_unlocked()
        data[kind] = {"at": time.time(), **(payload or {})}
        write_text_atomic(_path(), json.dumps(data, indent=2))
        return data
