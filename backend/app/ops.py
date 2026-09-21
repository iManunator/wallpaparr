"""Lightweight ops snapshot (last cron, last generate) for the dashboard."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

def _path() -> Path:
    from app.config import DATA_DIR, ensure_dirs

    ensure_dirs()
    return DATA_DIR / "ops.json"


def load_ops() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def record_event(kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = load_ops()
    data[kind] = {"at": time.time(), **(payload or {})}
    from app.fsutil import write_text_atomic

    write_text_atomic(_path(), json.dumps(data, indent=2))
    return data
