"""License-safe cinematic stills for the built-in demo catalog.

Sources are Wikimedia Commons (NASA, NARA, Library of Congress, and one
CC BY-SA photograph). Nothing here is scraped from a commercial studio.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models import MediaItem

STILLS_DIR = Path(__file__).resolve().parent / "demo_stills"
CATALOG_PATH = STILLS_DIR / "catalog.json"

TITLE_SLUGS = {
    "Northlight": "northlight",
    "Harbor Season": "harbor-season",
    "Glass Orchard": "glass-orchard",
    "Signal Country": "signal-country",
    "Paper Atlas": "paper-atlas",
    "Night Relay": "night-relay",
}


@lru_cache(maxsize=1)
def load_catalog() -> list[dict]:
    if not CATALOG_PATH.is_file():
        return []
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def still_path(slug_or_id: str | None) -> Path | None:
    if not slug_or_id:
        return None
    key = slug_or_id.strip().lower()
    for row in load_catalog():
        names = {
            str(row.get("id") or "").lower(),
            str(row.get("slug") or "").lower(),
            str(row.get("file") or "").lower().removesuffix(".jpg"),
            str(row.get("title") or "").lower(),
        }
        if key in names:
            path = STILLS_DIR / str(row.get("file") or "")
            return path if path.is_file() else None
    # Direct filename / slug fallback so tests can request northlight.jpg.
    for candidate in (STILLS_DIR / key, STILLS_DIR / f"{key}.jpg"):
        if candidate.is_file():
            return candidate
    return None


def still_bytes(slug_or_id: str | None) -> bytes | None:
    path = still_path(slug_or_id)
    if path is None:
        return None
    return path.read_bytes()


def logo_path(slug_or_id: str | None) -> Path | None:
    """License-safe demo clearlogo (Northlight). Other titles fall back to text."""
    if not slug_or_id:
        return None
    key = slug_or_id.strip().lower()
    aliases = {
        "demo-jf-1",
        "northlight",
        "northlight-logo",
        "90001",
        "tt9000001",
    }
    if key not in aliases:
        return None
    path = STILLS_DIR / "northlight-logo.png"
    return path if path.is_file() else None


def logo_bytes(slug_or_id: str | None) -> bytes | None:
    path = logo_path(slug_or_id)
    if path is None:
        return None
    return path.read_bytes()


def logo_path_for_item(item: MediaItem) -> Path | None:
    keys = [item.jellyfin_id, item.tmdb_id, item.imdb_id, TITLE_SLUGS.get(item.title), item.title]
    for key in keys:
        found = logo_path(key)
        if found:
            return found
    return None


def logo_bytes_for_item(item: MediaItem) -> bytes | None:
    path = logo_path_for_item(item)
    if path is None:
        return None
    return path.read_bytes()


def still_path_for_item(item: MediaItem) -> Path | None:
    keys = [item.jellyfin_id, item.tmdb_id, item.imdb_id]
    demoish = (item.jellyfin_id or "").lower().startswith("demo-") or item.source == "demo"
    if demoish:
        keys.extend([TITLE_SLUGS.get(item.title), item.title])
    for key in keys:
        found = still_path(key)
        if found:
            return found
    return None


def attach_demo_art(item: MediaItem) -> MediaItem:
    path = still_path_for_item(item)
    logo = logo_path_for_item(item)
    updates: dict = {}
    if path is not None:
        updates["backdrop_path"] = str(path)
        updates["backdrop_url"] = item.backdrop_url or f"/api/media/artwork/{item.jellyfin_id or path.stem}"
    if logo is not None:
        updates["logo_url"] = item.logo_url or f"/api/media/logo/{item.jellyfin_id or logo.stem}"
    if not updates:
        return item
    return item.model_copy(update=updates)


def public_catalog() -> dict:
    items = []
    for row in load_catalog():
        items.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "slug": row.get("slug"),
                "file": row.get("file"),
                "artwork": row.get("commons_title") or row.get("commons"),
                "artist": row.get("artist"),
                "credit": row.get("credit"),
                "license": row.get("license"),
                "license_url": row.get("license_url") or None,
                "attribution_required": bool(row.get("attribution_required")),
                "source_url": row.get("commons_page"),
                "artwork_url": f"/api/media/artwork/{row.get('id') or row.get('slug')}",
                "logo_url": f"/api/media/logo/{row.get('id')}" if logo_path(str(row.get("id") or "")) else None,
                "title_fallback": "text" if not logo_path(str(row.get("id") or "")) else "logo",
            }
        )
    return {
        "ok": True,
        "count": len(items),
        "attribution": "/api/demo/attribution",
        "note": "Demo stills are NASA / NARA / Library of Congress public-domain photographs plus one CC BY-SA image. No commercial studio artwork. Only Northlight ships a license-safe original clearlogo PNG; other titles fall back to title text.",
        "items": items,
    }
