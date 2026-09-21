"""Skip / replace / cleanup generated wallpapers by media id."""

from __future__ import annotations

from app.models import MediaItem, WallpaperRecord
from app.seerr_status import seerr_kind
from app.watch import normalize_watch_state


def media_ids_of(item: MediaItem) -> set[str]:
    return {
        value.lower()
        for value in (item.jellyfin_id, item.tmdb_id, item.imdb_id)
        if value
    }


def matching_records(catalog: list[WallpaperRecord], item: MediaItem, layout: str | None = None) -> list[WallpaperRecord]:
    ids = media_ids_of(item)
    if not ids:
        title_key = item.title.strip().lower()
        year = item.year
        return [
            rec
            for rec in catalog
            if rec.title.strip().lower() == title_key
            and (year is None or rec.year == year)
            and (layout is None or rec.layout.lower() == layout.lower())
        ]
    return [
        rec
        for rec in catalog
        if rec.media_ids() & ids and (layout is None or rec.layout.lower() == layout.lower())
    ]


def _norm(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_").replace("-", "_")


def status_fingerprint(
    *,
    watch_state: str | None = None,
    library_state: str | None = None,
    availability: str | None = None,
    source: str | None = None,
) -> tuple[str, str, str, str]:
    """Chrome-facing status tuple used to detect watch / availability changes."""
    return (
        normalize_watch_state(watch_state) or "",
        seerr_kind(library_state, availability, source) or "",
        _norm(availability),
        _norm(library_state),
    )


def status_changed(rec: WallpaperRecord, item: MediaItem) -> bool:
    """True when baked chrome would change (watch and/or availability)."""
    return status_fingerprint(
        watch_state=rec.watch_state,
        library_state=rec.library_state,
        availability=rec.availability,
        source=rec.source,
    ) != status_fingerprint(
        watch_state=item.watch_state,
        library_state=item.library_state,
        availability=item.availability,
        source=item.source,
    )


def should_skip(
    catalog: list[WallpaperRecord],
    item: MediaItem,
    layout: str,
    skip_existing: bool,
    *,
    refresh_status: bool = False,
) -> bool:
    if not skip_existing:
        return False
    matches = matching_records(catalog, item, layout)
    if not matches:
        return False
    if refresh_status and any(status_changed(rec, item) for rec in matches):
        return False
    return True


def records_to_cleanup(
    catalog: list[WallpaperRecord],
    current_items: list[MediaItem],
    layout: str,
) -> list[WallpaperRecord]:
    """Records for ``layout`` whose title is no longer in ``current_items``.

    Scoped to the source(s) actually fetched this run (derived from
    ``current_items``, not the caller's ``source=`` string — demo mixes
    jellyfin/jellyseerr/plex-labeled fixtures). Without this, cleaning up
    after a Jellyfin-only batch would delete every Seerr-sourced wallpaper
    in the layout (and vice versa), since they were never in ``keep``.
    """
    keep: set[str] = set()
    sources: set[str] = set()
    for item in current_items:
        keep |= media_ids_of(item)
        keep.add(f"{item.title.strip().lower()}|{item.year or ''}")
        sources.add((item.source or "").strip().lower())
    doomed = []
    for rec in catalog:
        if rec.layout.lower() != layout.lower():
            continue
        # Records with no recorded source (older rows) stay eligible for
        # cleanup as before; only a *known*, different source is protected.
        if sources and rec.source and rec.source.strip().lower() not in sources:
            continue
        rec_ids = rec.media_ids()
        title_key = f"{rec.title.strip().lower()}|{rec.year or ''}"
        if rec_ids and rec_ids & keep:
            continue
        if not rec_ids and title_key in keep:
            continue
        doomed.append(rec)
    return doomed
