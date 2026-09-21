"""Seerr / requestable chrome chips.

Maps existing catalog fields (``library_state``, ``availability``, ``source``)
onto one obvious wallpaper pill so titles that are only on Seerr — not in the
library — read as clearly as Unwatched / Partly watched / Watched.

Does not invent statuses: Jellyfin/Seerr providers already set
``seerr_only`` / ``in_library`` and ``requestable`` / ``available``.
"""

from __future__ import annotations

from typing import Any

LIBRARY_SEERR_ONLY = frozenset({"seerr_only", "not_in_library"})
AVAIL_REQUESTABLE = frozenset({"requestable", "not_available"})
AVAIL_UPCOMING = frozenset({"upcoming"})
SOURCE_SEERR = frozenset({"jellyseerr", "seerr"})
LIBRARY_IN = frozenset({"in_library", "available"})

TONES: dict[str, dict[str, str]] = {
    "seerr_only": {"label": "Seerr only", "color": "#c4a5ff"},
    "requestable": {"label": "Requestable", "color": "#f0a36b"},
    "on_seerr": {"label": "On Seerr", "color": "#8eb4ff"},
    "upcoming": {"label": "Upcoming", "color": "#f2c94c"},
}


def _norm(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_").replace("-", "_")


def seerr_kind(
    library_state: str | None = None,
    availability: str | None = None,
    source: str | None = None,
) -> str | None:
    """Most specific Seerr chrome id, or None when the title is in-library."""
    library = _norm(library_state)
    avail = _norm(availability)
    src = _norm(source)
    in_library = library in LIBRARY_IN
    if avail in AVAIL_UPCOMING:
        return "upcoming"
    if library in LIBRARY_SEERR_ONLY:
        return "seerr_only"
    if avail in AVAIL_REQUESTABLE:
        return "requestable"
    if src in SOURCE_SEERR and not in_library:
        return "on_seerr"
    return None


def seerr_badge(
    library_state: str | None = None,
    availability: str | None = None,
    source: str | None = None,
) -> dict[str, str] | None:
    kind = seerr_kind(library_state, availability, source)
    if not kind:
        return None
    meta = TONES[kind]
    return {"id": kind, "label": meta["label"], "color": meta["color"]}


def seerr_label(
    library_state: str | None = None,
    availability: str | None = None,
    source: str | None = None,
) -> str:
    badge = seerr_badge(library_state, availability, source)
    return badge["label"] if badge else ""


def seerr_payload(
    library_state: str | None = None,
    availability: str | None = None,
    source: str | None = None,
) -> dict[str, Any] | None:
    badge = seerr_badge(library_state, availability, source)
    return dict(badge) if badge else None
