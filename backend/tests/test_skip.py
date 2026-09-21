from __future__ import annotations

from app.models import MediaItem, WallpaperRecord
from app.skip import matching_records, records_to_cleanup, should_skip, status_changed


def test_skip_by_jellyfin_id():
    catalog = [
        WallpaperRecord(id="1", layout="Netflix Hero", filename="a.jpg", title="Northlight", jellyfin_id="demo-jf-1")
    ]
    item = MediaItem(title="Northlight Recut", jellyfin_id="demo-jf-1")
    assert should_skip(catalog, item, "Netflix Hero", True)
    assert not should_skip(catalog, item, "Netflix Hero", False)


def test_skip_by_tmdb_id_across_title_changes():
    catalog = [
        WallpaperRecord(id="1", layout="Netflix Hero", filename="a.jpg", title="Old", tmdb_id="90004")
    ]
    item = MediaItem(title="New Name", tmdb_id="90004")
    assert matching_records(catalog, item, "Netflix Hero")[0].id == "1"


def test_cleanup_drops_titles_not_in_current_list():
    catalog = [
        WallpaperRecord(id="keep", layout="A", filename="a.jpg", title="Keep", jellyfin_id="1"),
        WallpaperRecord(id="drop", layout="A", filename="b.jpg", title="Drop", jellyfin_id="2"),
        WallpaperRecord(id="other", layout="B", filename="c.jpg", title="Other", jellyfin_id="2"),
    ]
    current = [MediaItem(title="Keep", jellyfin_id="1")]
    doomed = records_to_cleanup(catalog, current, "A")
    assert [d.id for d in doomed] == ["drop"]


def test_cleanup_does_not_touch_other_sources():
    """Running cleanup for one source (e.g. Jellyfin) must not delete
    wallpapers that came from a different source (e.g. Jellyseerr) in the
    same layout — they were never part of this batch's fetch."""
    catalog = [
        WallpaperRecord(id="jf-keep", layout="A", filename="a.jpg", title="JF Keep", jellyfin_id="1", source="jellyfin"),
        WallpaperRecord(id="jf-drop", layout="A", filename="b.jpg", title="JF Drop", jellyfin_id="2", source="jellyfin"),
        WallpaperRecord(id="seerr-untouched", layout="A", filename="c.jpg", title="Seerr Title", tmdb_id="90004", source="jellyseerr"),
    ]
    current = [MediaItem(title="JF Keep", jellyfin_id="1", source="jellyfin")]
    doomed = records_to_cleanup(catalog, current, "A")
    assert [d.id for d in doomed] == ["jf-drop"]


def test_status_changed_watch_and_availability():
    rec = WallpaperRecord(
        id="1",
        layout="Netflix Hero",
        filename="a.jpg",
        title="Show",
        jellyfin_id="jf-1",
        tmdb_id="100",
        watch_state="unwatched",
        availability="requestable",
        library_state="seerr_only",
        source="jellyseerr",
    )
    same = MediaItem(
        title="Show",
        jellyfin_id="jf-1",
        tmdb_id="100",
        watch_state="unwatched",
        availability="requestable",
        library_state="seerr_only",
        source="jellyseerr",
    )
    watched = MediaItem(
        title="Show",
        jellyfin_id="jf-1",
        tmdb_id="100",
        watch_state="watched",
        availability="available",
        library_state="in_library",
        source="jellyfin",
    )
    available = MediaItem(
        title="Show",
        jellyfin_id="jf-1",
        tmdb_id="100",
        watch_state="unwatched",
        availability="available",
        library_state="in_library",
        source="jellyfin",
    )
    assert not status_changed(rec, same)
    assert status_changed(rec, watched)
    assert status_changed(rec, available)


def test_refresh_status_bypasses_skip_when_changed():
    catalog = [
        WallpaperRecord(
            id="1",
            layout="Netflix Hero",
            filename="a.jpg",
            title="Show",
            jellyfin_id="jf-1",
            watch_state="unwatched",
            availability="requestable",
            library_state="seerr_only",
            source="jellyseerr",
        )
    ]
    changed = MediaItem(
        title="Show",
        jellyfin_id="jf-1",
        watch_state="watched",
        availability="available",
        library_state="in_library",
        source="jellyfin",
    )
    unchanged = MediaItem(
        title="Show",
        jellyfin_id="jf-1",
        watch_state="unwatched",
        availability="requestable",
        library_state="seerr_only",
        source="jellyseerr",
    )
    assert should_skip(catalog, changed, "Netflix Hero", True, refresh_status=False)
    assert not should_skip(catalog, changed, "Netflix Hero", True, refresh_status=True)
    assert should_skip(catalog, unchanged, "Netflix Hero", True, refresh_status=True)
