from app.watch import normalize_watch_state, watch_badge, watch_label


def test_normalize_watch_aliases():
    assert normalize_watch_state("unplayed") == "unwatched"
    assert normalize_watch_state("in_progress") == "partial"
    assert normalize_watch_state("Partially Watched") == "partial"
    assert normalize_watch_state("played") == "watched"
    assert normalize_watch_state("") is None
    assert normalize_watch_state(None) is None


def test_watch_badge_labels_and_colors():
    unwatched = watch_badge("unwatched")
    partial = watch_badge("partial")
    watched = watch_badge("watched")
    assert unwatched and unwatched["label"] == "Unwatched"
    assert partial and partial["label"] == "Partly watched"
    assert watched and watched["label"] == "Watched"
    assert unwatched["color"] != partial["color"] != watched["color"]
    assert watch_label("unwatched") == "Unwatched"
    assert watch_badge("mystery") is None
