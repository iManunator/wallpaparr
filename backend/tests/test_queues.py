from __future__ import annotations

import random

from app.models import WallpaperRecord
from app.queues import (
    TASTE_PRESETS,
    candidates_for_queue,
    pick_taste,
    queue_ids_for,
    resolve_taste_weights,
    summarize_queues,
)
from app.selection import SelectionQuery, apply_pool, select_wallpaper


def _rec(**kwargs) -> WallpaperRecord:
    defaults = dict(
        id="x",
        layout="Netflix Hero",
        filename="x.jpg",
        title="X",
        year=2020,
        rating=7.0,
        genres=["Drama"],
        official_rating="PG",
        watch_state="unwatched",
        library_state="in_library",
        source="jellyfin",
        mtime=1.0,
    )
    defaults.update(kwargs)
    return WallpaperRecord(**defaults)


def test_queue_ids_unwatched_and_requestable():
    unwatched = _rec(watch_state="unwatched")
    requestable = _rec(
        watch_state="unwatched",
        library_state="seerr_only",
        availability="requestable",
        source="jellyseerr",
    )
    assert "unwatched" in queue_ids_for(unwatched)
    assert "newly_added" not in queue_ids_for(unwatched)
    assert "requestable" in queue_ids_for(requestable)
    assert "seerr_trending" in queue_ids_for(requestable)


def test_pinned_pool_does_not_fallback():
    catalog = [_rec(id="1", title="Loose", pinned=False)]
    picked = select_wallpaper(catalog, SelectionQuery(layout="Netflix Hero", pool="pinned"))
    assert picked is None
    assert apply_pool(catalog, "pinned", fallback=False) == []


def test_hidden_titles_never_selected():
    catalog = [
        _rec(id="1", filename="a.jpg", title="Shown", rating=5, mtime=1),
        _rec(id="2", filename="b.jpg", title="Buried", rating=9, hidden=True, mtime=2),
    ]
    picked = select_wallpaper(catalog, SelectionQuery(layout="Netflix Hero", sort="rating"))
    assert picked is not None
    assert picked.title == "Shown"


def test_taste_tonight_picks_from_weighted_queues(seeded_catalog):
    rec, qid = pick_taste(
        seeded_catalog,
        "Netflix Hero",
        TASTE_PRESETS["tonight"],
        rng=random.Random(3),
    )
    assert rec is not None
    assert rec.hidden is False
    assert qid in TASTE_PRESETS["tonight"]


def test_taste_via_pool_prefix(seeded_catalog):
    picked = select_wallpaper(
        seeded_catalog,
        SelectionQuery(layout="Netflix Hero", pool="taste:unwatched_heavy"),
        rng=random.Random(1),
    )
    assert picked is not None
    assert picked.watch_state in {"unwatched", "partial"}


def test_profile_query(seeded_catalog):
    picked = select_wallpaper(
        seeded_catalog,
        SelectionQuery(layout="Netflix Hero", profile="cinephile"),
        rng=random.Random(2),
    )
    assert picked is not None


def test_continue_watching_and_newly_added(seeded_catalog):
    cont = select_wallpaper(
        seeded_catalog,
        SelectionQuery(layout="Netflix Hero", pool="continue_watching"),
    )
    assert cont is not None
    assert cont.title == "Harbor Season"
    newest = select_wallpaper(
        seeded_catalog,
        SelectionQuery(layout="Netflix Hero", pool="newly_added"),
    )
    assert newest is not None
    assert newest.title == "Northlight"


def test_summarize_queues_counts(seeded_catalog):
    views = {v.id: v for v in summarize_queues(seeded_catalog, "Netflix Hero")}
    assert views["unwatched"].count == 1
    assert views["continue_watching"].count == 1
    assert views["pinned"].count == 0
    assert "Northlight" in views["newly_added"].titles


def test_candidates_seerr_does_not_fallback_to_jellyfin(seeded_catalog):
    items = candidates_for_queue(seeded_catalog, "Netflix Hero", "seerr_trending")
    assert items == []


def test_resolve_taste_weights_custom_and_unknown():
    custom = resolve_taste_weights(None, {"unwatched": 80, "nope": 20})
    assert custom == {"unwatched": 80}
    assert resolve_taste_weights("missing") == TASTE_PRESETS["tonight"]


def test_select_wallpaper_honors_custom_taste_weights(seeded_catalog):
    picked = select_wallpaper(
        seeded_catalog,
        SelectionQuery(
            layout="Netflix Hero",
            profile="tonight",
            taste_weights={"continue_watching": 100},
        ),
        rng=random.Random(1),
    )
    assert picked is not None
    assert picked.title == "Harbor Season"


def test_pin_bias_only_when_rng_supplied():
    catalog = [
        _rec(id="1", filename="a.jpg", title="Pinned", pinned=True, rating=1),
        _rec(id="2", filename="b.jpg", title="Other", pinned=False, rating=9),
    ]
    deterministic = select_wallpaper(
        catalog,
        SelectionQuery(layout="Netflix Hero", sort="rating"),
    )
    assert deterministic is not None
    assert deterministic.title == "Other"
    biased = select_wallpaper(
        catalog,
        SelectionQuery(layout="Netflix Hero", sort="random"),
        rng=random.Random(0),
    )
    assert biased is not None
    assert biased.title in {"Pinned", "Other"}
