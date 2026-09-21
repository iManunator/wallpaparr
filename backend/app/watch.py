"""Watch-state badges (unwatched / partial / watched).

Jellyfin UserData and demo fixtures store a free-form ``watch_state``.
The UI, still renderer, and smart queues all normalize through this module
so pills stay consistent across gallery, editor, and baked JPEGs.
"""

from __future__ import annotations

from typing import Any

WATCH_UNWATCHED = frozenset({"unwatched", "unplayed"})
WATCH_PARTIAL = frozenset({"partial", "partially_watched", "inprogress", "in_progress"})
WATCH_WATCHED = frozenset({"watched", "played"})

TONES: dict[str, dict[str, str]] = {
    "unwatched": {"label": "Unwatched", "color": "#7ad0c4"},
    "partial": {"label": "Partly watched", "color": "#e2b657"},
    "watched": {"label": "Watched", "color": "#87c38f"},
}


def normalize_watch_state(value: str | None) -> str | None:
    key = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key in WATCH_UNWATCHED:
        return "unwatched"
    if key in WATCH_PARTIAL:
        return "partial"
    if key in WATCH_WATCHED:
        return "watched"
    return None


def watch_badge(value: str | None) -> dict[str, str] | None:
    kind = normalize_watch_state(value)
    if not kind:
        return None
    meta = TONES[kind]
    return {"id": kind, "label": meta["label"], "color": meta["color"]}


def watch_label(value: str | None) -> str:
    badge = watch_badge(value)
    return badge["label"] if badge else ""


def watch_color(value: str | None) -> str:
    badge = watch_badge(value)
    return badge["color"] if badge else "#ffffff"


def watch_payload(value: str | None) -> dict[str, Any] | None:
    badge = watch_badge(value)
    return dict(badge) if badge else None
