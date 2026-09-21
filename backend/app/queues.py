"""Smart queues and taste profiles for Wallpaparr.

Queues are first-class views over the catalog (Unwatched, Continue watching,
Newly added, Seerr trending, Requestable, Pinned). Taste profiles pick a
queue with weighted probability, then a title inside it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.models import WallpaperRecord
from app.selection import apply_pool, matches_layout, pick_sorted, visible_records

QUEUE_DEFS: dict[str, dict[str, str | None]] = {
    "unwatched": {"label": "Unwatched", "pool": "unwatched", "sort": "random"},
    "continue_watching": {"label": "Continue watching", "pool": "partial", "sort": "random"},
    "watched": {"label": "Watched", "pool": "watched", "sort": "random"},
    "newly_added": {"label": "Newly added", "pool": None, "sort": "latest"},
    "seerr_trending": {"label": "Seerr trending", "pool": "source:jellyseerr", "sort": "rating"},
    "requestable": {"label": "Requestable", "pool": "requestable", "sort": "random"},
    "pinned": {"label": "Pinned", "pool": "pinned", "sort": "random"},
}

TASTE_PRESETS: dict[str, dict[str, int]] = {
    "tonight": {"unwatched": 30, "continue_watching": 20, "watched": 15, "newly_added": 20, "seerr_trending": 15},
    "unwatched_heavy": {"unwatched": 70, "continue_watching": 20, "newly_added": 10},
    "cinephile": {"unwatched": 40, "newly_added": 20, "seerr_trending": 40},
    "discovery": {"requestable": 50, "seerr_trending": 50},
}


@dataclass(frozen=True)
class QueueView:
    id: str
    label: str
    count: int
    titles: list[str]


def queue_ids_for(record: WallpaperRecord) -> list[str]:
    hits = []
    for qid, spec in QUEUE_DEFS.items():
        if qid == "newly_added":
            continue
        pool = spec.get("pool")
        if pool and apply_pool([record], str(pool), fallback=False) == [record]:
            hits.append(qid)
    return hits


def candidates_for_queue(
    catalog: list[WallpaperRecord],
    layout: str | None,
    queue_id: str,
) -> list[WallpaperRecord]:
    spec = QUEUE_DEFS.get(queue_id)
    if not spec:
        return []
    existing = visible_records([r for r in catalog if not layout or matches_layout(r, layout)])
    pool = spec.get("pool")
    if not pool:
        return list(existing)
    return apply_pool(existing, str(pool), fallback=False)


def summarize_queues(catalog: list[WallpaperRecord], layout: str | None = None) -> list[QueueView]:
    records = visible_records(catalog)
    if layout:
        records = [r for r in records if matches_layout(r, layout)]
    views = []
    for qid, spec in QUEUE_DEFS.items():
        if qid == "newly_added":
            items = sorted(records, key=lambda r: r.mtime, reverse=True)[:12]
        elif spec.get("pool"):
            items = apply_pool(records, str(spec["pool"]), fallback=False)
        else:
            items = list(records)
        views.append(
            QueueView(
                id=qid,
                label=str(spec["label"]),
                count=len(items),
                titles=[r.title for r in items[:4]],
            )
        )
    return views


def pick_taste(
    catalog: list[WallpaperRecord],
    layout: str | None,
    weights: dict[str, int] | None,
    rng: random.Random | None = None,
    exclude: str | None = None,
) -> tuple[WallpaperRecord | None, str | None]:
    """Weighted mix of queues. Returns (record, queue_id)."""
    from app.selection import apply_exclude

    chooser = rng or random.Random()
    mix = weights or TASTE_PRESETS["tonight"]
    buckets: list[tuple[int, str, list[WallpaperRecord]]] = []
    for qid, weight in mix.items():
        w = int(weight or 0)
        if w <= 0 or qid not in QUEUE_DEFS:
            continue
        items = apply_exclude(candidates_for_queue(catalog, layout, qid), exclude)
        if items:
            buckets.append((w, qid, items))
    if not buckets:
        fallback = visible_records([r for r in catalog if not layout or matches_layout(r, layout)])
        fallback = apply_exclude(fallback, exclude)
        if not fallback:
            return None, None
        return pick_sorted(fallback, "random", rng=chooser), None
    total = sum(b[0] for b in buckets)
    dart = chooser.randrange(total)
    acc = 0
    chosen_id = buckets[0][1]
    chosen_items = buckets[0][2]
    for weight, qid, items in buckets:
        acc += weight
        if dart < acc:
            chosen_id = qid
            chosen_items = items
            break
    sort = str(QUEUE_DEFS[chosen_id].get("sort") or "random")
    return pick_sorted(chosen_items, sort, rng=chooser), chosen_id


def resolve_taste_weights(profile: str | None, custom: dict[str, int] | None = None) -> dict[str, int]:
    if custom:
        return {k: int(v) for k, v in custom.items() if k in QUEUE_DEFS}
    key = (profile or "tonight").strip().lower()
    return dict(TASTE_PRESETS.get(key) or TASTE_PRESETS["tonight"])
