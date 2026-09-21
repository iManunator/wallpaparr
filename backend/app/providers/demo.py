"""Built-in demo catalog so the suite works without Jellyfin in CI / first boot."""

from __future__ import annotations

from app.demo_art import attach_demo_art
from app.models import MediaItem

DEMO_ITEMS = [
    MediaItem(
        title="Northlight",
        year=2024,
        overview="A cartographer maps a city that rearranges itself after dusk.",
        rating=8.4,
        genres=["Sci-Fi", "Mystery"],
        official_rating="PG-13",
        runtime="2h 11m",
        watch_state="unwatched",
        library_state="in_library",
        availability="available",
        source="jellyfin",
        jellyfin_id="demo-jf-1",
        tmdb_id="90001",
        imdb_id="tt9000001",
        action_url="jellyfin://items/demo-jf-1",
    ),
    MediaItem(
        title="Harbor Season",
        year=2022,
        overview="Dockworkers keep a coastal town running through an impossible winter.",
        rating=7.9,
        genres=["Drama"],
        official_rating="TV-14",
        runtime="48m",
        media_type="tv",
        watch_state="partial",
        library_state="in_library",
        availability="available",
        source="jellyfin",
        jellyfin_id="demo-jf-2",
        tmdb_id="90002",
        action_url="jellyfin://items/demo-jf-2",
    ),
    MediaItem(
        title="Glass Orchard",
        year=2018,
        overview="A botanist inherits a greenhouse that grows memories instead of fruit.",
        rating=8.1,
        genres=["Fantasy", "Drama"],
        official_rating="PG",
        runtime="1h 58m",
        watch_state="watched",
        library_state="in_library",
        availability="available",
        source="jellyfin",
        jellyfin_id="demo-jf-3",
        tmdb_id="90003",
        action_url="jellyfin://items/demo-jf-3",
    ),
    MediaItem(
        title="Signal Country",
        year=2023,
        overview="A radio host in the desert starts receiving tomorrow's news.",
        rating=7.6,
        genres=["Thriller", "Sci-Fi"],
        official_rating="TV-MA",
        runtime="52m",
        media_type="tv",
        watch_state="unwatched",
        # Mixed Seerr fixture: not in the library, requestable on Jellyseerr.
        library_state="seerr_only",
        availability="requestable",
        source="jellyseerr",
        jellyfin_id="demo-jf-4",
        tmdb_id="90004",
        action_url="https://seerr.example/tv/90004",
    ),
    MediaItem(
        title="Paper Atlas",
        year=1999,
        overview="Rival mapmakers race to chart a continent that refuses to stay still.",
        rating=6.4,
        genres=["Adventure", "Comedy"],
        official_rating="PG",
        runtime="1h 42m",
        watch_state="watched",
        library_state="in_library",
        availability="available",
        source="plex",
        jellyfin_id="demo-jf-5",
        imdb_id="tt9000005",
    ),
    MediaItem(
        title="Night Relay",
        year=2021,
        overview="Couriers on magnetic bikes deliver secrets across a sleepless megacity.",
        rating=8.7,
        genres=["Action", "Sci-Fi"],
        official_rating="PG-13",
        runtime="2h 4m",
        watch_state="unwatched",
        library_state="in_library",
        availability="available",
        source="jellyseerr",
        jellyfin_id="demo-jf-6",
        tmdb_id="90006",
        action_url="jellyfin://items/demo-jf-6",
    ),
]


class DemoProvider:
    name = "demo"

    def is_configured(self) -> bool:
        return True

    def test(self) -> dict:
        return {"ok": True, "server": "Demo catalog"}

    def list_items(self, limit: int = 40) -> list[MediaItem]:
        return [attach_demo_art(item) for item in DEMO_ITEMS[:limit]]
