"""Wallpaper selection: filters, pools, exclude, and sort/pick.

Mirrors the Projectivy-facing contract used by the TV Background Suite plugin:
`sort`, `pool`, `exclude`, genre/age/year/rating filters.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

from app.models import WallpaperRecord


VALID_SORTS = frozenset(
    {
        "random",
        "latest",
        "newest",
        "mtime_desc",
        "oldest",
        "mtime_asc",
        "rating",
        "rating_high",
        "rating_desc",
        "rating_asc",
        "rating_low",
        "year",
        "year_desc",
        "year_asc",
        "year_old",
    }
)

WATCH_UNWATCHED = frozenset({"unwatched", "unplayed"})
WATCH_PARTIAL = frozenset({"partial", "partially_watched", "inprogress", "in_progress"})
WATCH_WATCHED = frozenset({"watched", "played"})


@dataclass(frozen=True)
class SelectionQuery:
    layout: str | None
    genre: str | None = None
    age_rating: str | None = None
    min_year: int | None = None
    max_year: int | None = None
    min_rating: float | None = None
    max_rating: float | None = None
    sort: str = "random"
    pool: str | None = None
    exclude: str | None = None
    profile: str | None = None


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _alnum(value: str | None) -> str:
    return "".join(ch for ch in _norm(value) if ch.isalnum())


def matches_layout(record: WallpaperRecord, layout: str) -> bool:
    return _norm(record.layout) == _norm(layout)


def apply_pool(
    records: list[WallpaperRecord],
    pool: str | None,
    *,
    fallback: bool = True,
) -> list[WallpaperRecord]:
    if not pool:
        return list(records)
    key = _norm(pool)
    before = list(records)
    if key == "unwatched":
        filtered = [r for r in records if _norm(r.watch_state) in WATCH_UNWATCHED]
    elif key in ("partial", "partially_watched", "continue_watching"):
        filtered = [r for r in records if _norm(r.watch_state) in WATCH_PARTIAL]
    elif key == "watched":
        filtered = [r for r in records if _norm(r.watch_state) in WATCH_WATCHED]
    elif key == "pinned":
        return [r for r in records if r.pinned]
    elif key == "in_library":
        filtered = [
            r
            for r in records
            if _norm(r.library_state) == "in_library" or r.jellyfin_id or _norm(r.source) == "jellyfin"
        ]
    elif key in ("seerr_only", "not_in_library"):
        filtered = [
            r
            for r in records
            if _norm(r.library_state) in ("seerr_only", "not_in_library")
            or (_norm(r.source) in ("jellyseerr", "seerr") and not r.jellyfin_id)
        ]
    elif key == "requestable":
        filtered = [
            r
            for r in records
            if _norm(r.availability) in ("not_available", "requestable")
            or _norm(r.library_state) == "seerr_only"
        ]
    elif key in ("available", "available_seerr"):
        filtered = [r for r in records if _norm(r.availability) in ("available", "available_seerr")]
    elif key == "upcoming":
        filtered = [r for r in records if _norm(r.availability) == "upcoming"]
    elif key.startswith("source:"):
        want = key.split(":", 1)[1].strip()
        if want in ("seerr", "jellyseerr"):
            want = "jellyseerr"
        filtered = [
            r
            for r in records
            if _norm(r.source) == want
            or (want == "jellyseerr" and _norm(r.source) == "seerr")
            or want in _norm(r.source)
        ]
    else:
        filtered = list(records)
    if filtered:
        return filtered
    return before if fallback else []


def apply_rating(records: list[WallpaperRecord], min_rating: float | None, max_rating: float | None) -> list[WallpaperRecord]:
    if min_rating is None and max_rating is None:
        return list(records)
    lo = 0.0 if min_rating is None else float(min_rating)
    hi = 10.0 if max_rating is None else float(max_rating)
    return [r for r in records if lo <= float(r.rating or 0) <= hi]


def apply_year(records: list[WallpaperRecord], min_year: int | None, max_year: int | None) -> list[WallpaperRecord]:
    if min_year is None and max_year is None:
        return list(records)
    lo = 0 if min_year is None else int(min_year)
    hi = 9999 if max_year is None else int(max_year)
    return [r for r in records if lo <= int(r.year or 0) <= hi]


def apply_genre(records: list[WallpaperRecord], genre: str | None) -> list[WallpaperRecord]:
    terms = [_norm(part) for part in (genre or "").split(",") if part.strip()]
    if not terms:
        return list(records)
    out = []
    for record in records:
        blob = " ".join(_norm(g) for g in record.genres)
        if any(term in blob for term in terms):
            out.append(record)
    return out


def apply_age(records: list[WallpaperRecord], age_rating: str | None) -> list[WallpaperRecord]:
    terms = [_alnum(part) for part in (age_rating or "").split(",") if part.strip()]
    if not terms:
        return list(records)
    return [r for r in records if any(term in _alnum(r.official_rating) for term in terms)]


def _is_excluded(record: WallpaperRecord, tokens: list[str]) -> bool:
    path = record.filename.replace("\\", "/").lower()
    base = os.path.basename(path).lower()
    stem = os.path.splitext(base)[0]
    for token in tokens:
        token_base = os.path.basename(token)
        token_stem = os.path.splitext(token_base)[0]
        if token == path or token == base or token in path or token_stem == stem:
            return True
    return False


def apply_exclude(records: list[WallpaperRecord], exclude: str | None) -> list[WallpaperRecord]:
    """Filter out recently-shown wallpapers (the client's no-repeat bag).

    ``tokens`` is ordered most-recent first. When the whole bag empties the
    pool — common for small catalogs, since the bag (default depth 5) can
    cover the entire layout — that's not "nothing else available", it's just
    a bag deeper than the catalog. Falling back to the full list there would
    silently allow the wallpaper shown a moment ago to repeat immediately.
    Instead, only give back items excluded by anything *but* the single most
    recent pick, so a real repeat only happens when literally nothing else
    in the layout is left (the "only one background" case).
    """
    tokens = [t.strip().replace("\\", "/").lower() for t in (exclude or "").split(",") if t.strip()]
    if not tokens or len(records) <= 1:
        return list(records)
    narrowed = [r for r in records if not _is_excluded(r, tokens)]
    if narrowed:
        return narrowed
    most_recent = tokens[:1]
    narrowed = [r for r in records if not _is_excluded(r, most_recent)]
    return narrowed or list(records)


def pick_sorted(records: list[WallpaperRecord], sort: str, rng: random.Random | None = None) -> WallpaperRecord | None:
    if not records:
        return None
    mode = _norm(sort) or "random"
    items = list(records)
    if mode in ("year", "year_desc"):
        items.sort(key=lambda x: int(x.year or 0), reverse=True)
        return items[0]
    if mode in ("year_asc", "year_old"):
        items.sort(key=lambda x: int(x.year or 0))
        return items[0]
    if mode in ("rating", "rating_high", "rating_desc"):
        items.sort(key=lambda x: float(x.rating or 0), reverse=True)
        return items[0]
    if mode in ("rating_asc", "rating_low"):
        items.sort(key=lambda x: float(x.rating or 0))
        return items[0]
    if mode in ("latest", "newest", "mtime_desc"):
        items.sort(key=lambda x: float(x.mtime or 0), reverse=True)
        return items[0]
    if mode in ("oldest", "mtime_asc"):
        items.sort(key=lambda x: float(x.mtime or 0))
        return items[0]
    chooser = rng.choice if rng is not None else random.choice
    return chooser(items)


def visible_records(records: list[WallpaperRecord]) -> list[WallpaperRecord]:
    return [r for r in records if not r.hidden]


def select_wallpaper(
    catalog: list[WallpaperRecord],
    query: SelectionQuery,
    rng: random.Random | None = None,
) -> WallpaperRecord | None:
    existing = visible_records(
        [r for r in catalog if not query.layout or matches_layout(r, query.layout)]
    )
    if not existing:
        return None
    pool = query.pool
    sort = query.sort
    profile = query.profile
    if (pool or "").startswith("taste:"):
        profile = profile or pool.split(":", 1)[1]
        pool = None
    if profile:
        from app.queues import pick_taste, resolve_taste_weights

        rec, _qid = pick_taste(
            catalog,
            query.layout,
            resolve_taste_weights(profile),
            rng=rng,
            exclude=query.exclude,
        )
        return rec
    if pool == "newly_added":
        pool = None
        sort = "latest"
    if pool == "continue_watching":
        pool = "partial"
    strict = _norm(pool) == "pinned"
    filtered = apply_pool(existing, pool, fallback=not strict)
    filtered = apply_rating(filtered, query.min_rating, query.max_rating)
    filtered = apply_year(filtered, query.min_year, query.max_year)
    filtered = apply_genre(filtered, query.genre)
    filtered = apply_age(filtered, query.age_rating)
    filtered = apply_exclude(filtered, query.exclude)
    if not filtered:
        if strict:
            return None
        filtered = existing
    pinned = [r for r in filtered if r.pinned]
    if pinned and (pool == "pinned" or (rng.random() < 0.35 if rng else False)):
        filtered = pinned
    return pick_sorted(filtered, sort, rng=rng)


def unique_values(catalog: list[WallpaperRecord], field: str) -> list[str]:
    values: set[str] = set()
    for record in catalog:
        raw = getattr(record, field, None)
        if field == "genres" and isinstance(raw, list):
            values.update(str(v) for v in raw if v)
        elif raw not in (None, ""):
            values.add(str(raw))
    return sorted(values, key=lambda s: s.lower())
