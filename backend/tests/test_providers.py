from __future__ import annotations

from app.models import MediaItem
from app.providers.demo import DemoProvider
from app.providers.jellyfin import JellyfinProvider
from app.providers.seerr import SeerrProvider
from app.providers.tmdb import TmdbProvider


class FakeClient:
    def __init__(self, payload, by_url: dict | None = None):
        self.payload = payload
        self.by_url = by_url or {}

    def get_json(self, url, headers=None, params=None):
        for key, value in self.by_url.items():
            if key in url:
                return value
        return self.payload


def test_jellyfin_parses_watch_state_and_deep_link():
    payload = {
        "Items": [
            {
                "Id": "abc",
                "Name": "Dune",
                "ProductionYear": 2021,
                "Overview": "Sand",
                "CommunityRating": 8.5,
                "Genres": ["Sci-Fi"],
                "OfficialRating": "PG-13",
                "Type": "Movie",
                "RunTimeTicks": 155 * 60 * 10_000_000,
                "ProviderIds": {"Tmdb": "438631", "Imdb": "tt1160419"},
                "UserData": {"Played": False, "PlaybackPositionTicks": 0},
            }
        ]
    }
    provider = JellyfinProvider(url="http://jf:8096", api_key="k", user_id="u", client=FakeClient(payload))
    items = provider.list_items()
    assert len(items) == 1
    assert items[0].title == "Dune"
    assert items[0].year == 2021
    assert items[0].genres == ["Sci-Fi"]
    assert items[0].rating == 8.5
    assert items[0].official_rating == "PG-13"
    assert items[0].overview == "Sand"
    assert items[0].runtime == "2h 35m"
    assert items[0].media_type == "movie"
    assert items[0].watch_state == "unwatched"
    assert items[0].action_url == "jellyfin://items/abc"
    assert items[0].tmdb_id == "438631"
    assert items[0].source == "jellyfin"
    assert items[0].backdrop_url == "http://jf:8096/Items/abc/Images/Backdrop?maxWidth=1920"
    assert items[0].poster_url == "http://jf:8096/Items/abc/Images/Primary?maxHeight=600"
    assert items[0].logo_url == "http://jf:8096/Items/abc/Images/Logo"


def test_jellyfin_series_with_some_episodes_watched_is_partial():
    """Series/Season UserData has no PlaybackPositionTicks (that's per-video
    only) — Jellyfin reports aggregate progress via PlayedPercentage instead."""
    payload = {
        "Items": [
            {
                "Id": "series-partial",
                "Name": "Partly Through",
                "Type": "Series",
                "ProductionYear": 2021,
                "UserData": {"Played": False, "PlayedPercentage": 40.0},
            },
            {
                "Id": "series-none",
                "Name": "Not Started",
                "Type": "Series",
                "ProductionYear": 2021,
                "UserData": {"Played": False, "PlayedPercentage": 0},
            },
            {
                "Id": "series-done",
                "Name": "All Done",
                "Type": "Series",
                "ProductionYear": 2021,
                "UserData": {"Played": True, "PlayedPercentage": 100.0},
            },
        ]
    }
    items = JellyfinProvider(url="http://jf:8096", api_key="k", user_id="u", client=FakeClient(payload)).list_items()
    by_id = {i.jellyfin_id: i for i in items}
    assert by_id["series-partial"].watch_state == "partial"
    assert by_id["series-none"].watch_state == "unwatched"
    assert by_id["series-done"].watch_state == "watched"


def test_jellyfin_series_and_episode_metadata():
    payload = {
        "Items": [
            {
                "Id": "series-1",
                "Name": "From",
                "Type": "Series",
                "ProductionYear": 2022,
                "PremiereDate": "2022-02-20T00:00:00.0000000Z",
                "Genres": ["Science Fiction", "Horror", "Drama"],
                "CommunityRating": 8.494,
                "OfficialRating": "TV-MA",
                "Overview": "Nightmare town.",
                "RunTimeTicks": 51 * 60 * 10_000_000,
                "ProviderIds": {"Tmdb": "123"},
                "UserData": {},
                "ImageTags": {"Primary": "p", "Logo": "l"},
                "BackdropImageTags": ["b"],
            },
            {
                "Id": "ep-1",
                "Name": "Long Day's Journey Into Night",
                "SeriesName": "From",
                "Type": "Episode",
                "ProductionYear": 2023,
                "PremiereDate": "2023-04-23T00:00:00.0000000Z",
                "GenreItems": [{"Name": "Horror"}, {"Name": "Mystery"}],
                "CommunityRating": None,
                "CriticRating": 82,
                "OfficialRating": "TV-MA",
                "Overview": "Episode plot.",
                "RunTimeTicks": 50 * 60 * 10_000_000,
                "Series": {"ProductionYear": 2022, "PremiereDate": "2022-02-20T00:00:00.0000000Z"},
                "UserData": {"Played": False, "PlaybackPositionTicks": 10},
                "ImageTags": {"Primary": "p"},
                "BackdropImageTags": [],
            },
        ]
    }
    items = JellyfinProvider(url="http://jf:8096", api_key="k", user_id="u", client=FakeClient(payload)).list_items()
    by_id = {item.jellyfin_id: item for item in items}
    series = by_id["series-1"]
    assert series.media_type == "tv"
    assert series.year == 2022
    assert series.genres[:3] == ["Science Fiction", "Horror", "Drama"]
    assert series.rating == 8.494
    assert series.runtime == "51m"
    episode = by_id["ep-1"]
    assert episode.title == "From"
    assert episode.media_type == "tv"
    assert episode.year == 2022  # series year from nested Series
    assert episode.genres == ["Horror", "Mystery"]
    assert episode.rating == 8.2  # CriticRating 82 → 8.2
    assert episode.watch_state == "partial"
    assert episode.backdrop_url.endswith("/Primary?maxWidth=1920")


def test_jellyfin_premiere_date_and_skips_boxset():
    payload = {
        "Items": [
            {
                "Id": "no-year",
                "Name": "Arrival",
                "Type": "Movie",
                "PremiereDate": "2016-11-10T00:00:00.0000000Z",
                "Genres": ["Drama", "Science Fiction"],
                "CommunityRating": 7.6,
                "UserData": {},
            },
            {
                "Id": "box",
                "Name": "Avatar Filmreihe",
                "Type": "BoxSet",
                "ProductionYear": 2009,
                "Genres": ["Science Fiction"],
                "UserData": {},
            },
        ]
    }
    items = JellyfinProvider(url="http://jf:8096", api_key="k", user_id="u", client=FakeClient(payload)).list_items()
    assert len(items) == 1
    assert items[0].title == "Arrival"
    assert items[0].year == 2016
    assert items[0].genres == ["Drama", "Science Fiction"]


def test_seerr_marks_requestable_when_not_in_library():
    payload = {
        "results": [
            {
                "id": 55,
                "title": "The Menu",
                "mediaType": "movie",
                "releaseDate": "2022-11-18",
                "overview": "Dinner",
                "voteAverage": 7.2,
                "genreIds": [27, 53, 35],
                "backdropPath": "/x.jpg",
                "mediaInfo": {"status": "UNKNOWN"},
            }
        ]
    }
    provider = SeerrProvider(url="http://seerr:5055", api_key="k", client=FakeClient(payload))
    items = provider.list_items()
    assert items[0].library_state == "seerr_only"
    assert items[0].availability == "requestable"
    assert items[0].tmdb_id == "55"
    assert items[0].source == "jellyseerr"
    assert items[0].year == 2022
    assert items[0].genres == ["Horror", "Thriller", "Comedy"]
    assert items[0].action_url == "http://seerr:5055/movie/55"


def test_seerr_in_library_uses_jellyfin_action_for_moonfin():
    payload = {
        "results": [
            {
                "id": 90,
                "title": "In Library",
                "mediaType": "movie",
                "releaseDate": "2020-01-01",
                "voteAverage": 7,
                "mediaInfo": {"status": "available", "jellyfinMediaId": "jf-90"},
            }
        ]
    }
    item = SeerrProvider(url="http://seerr:5055", api_key="k", client=FakeClient(payload)).list_items()[0]
    assert item.jellyfin_id == "jf-90"
    assert item.action_url == "jellyfin://items/jf-90"


def test_seerr_reads_tmdb_shaped_logos():
    # The bulk /discover/trending listing never has images — only the
    # per-item /api/v1/movie/{id} detail endpoint does.
    discover = {
        "results": [
            {
                "id": 77,
                "title": "Clearmark",
                "mediaType": "movie",
                "releaseDate": "2021-01-01",
                "voteAverage": 8,
            }
        ]
    }
    detail = {
        "images": {
            "logos": [
                {"file_path": "/fr.png", "iso_639_1": "fr", "vote_average": 9},
                {"file_path": "/en-logo.png", "iso_639_1": "en", "vote_average": 2},
            ]
        },
    }
    client = FakeClient(discover, by_url={"/api/v1/movie/77": detail})
    item = SeerrProvider(url="http://seerr:5055", api_key="k", client=client).list_items()[0]
    assert item.logo_url == "https://image.tmdb.org/t/p/original/en-logo.png"


def test_seerr_extracts_imdb_id_from_detail_external_ids():
    discover = {"results": [{"id": 88, "title": "X", "mediaType": "movie", "voteAverage": 6}]}
    detail = {"externalIds": {"imdbId": "tt9999999"}}
    client = FakeClient(discover, by_url={"/api/v1/movie/88": detail})
    item = SeerrProvider(url="http://seerr:5055", api_key="k", client=client).list_items()[0]
    assert item.imdb_id == "tt9999999"


def test_seerr_enriches_with_omdb_when_imdb_id_and_key_present():
    discover = {"results": [{"id": 100, "title": "Ratings Test", "mediaType": "movie", "voteAverage": 7.5}]}
    detail = {"imdbId": "tt1234567"}
    omdb_payload = {
        "Response": "True",
        "Ratings": [
            {"Source": "Rotten Tomatoes", "Value": "92%"},
            {"Source": "Metacritic", "Value": "81/100"},
        ],
        "imdbRating": "8.4",
        "Awards": "Won 1 Oscar",
        "BoxOffice": "$100,000,000",
    }
    client = FakeClient(
        discover,
        by_url={"/api/v1/movie/100": detail, "omdbapi.com": omdb_payload},
    )
    item = SeerrProvider(
        url="http://seerr:5055", api_key="k", client=client, omdb_api_key="omdb-key",
    ).list_items()[0]
    assert item.imdb_id == "tt1234567"
    assert item.imdb_rating == 8.4
    assert item.rotten_tomatoes == 92
    assert item.metacritic == 81
    assert item.awards == "Won 1 Oscar"
    assert item.box_office == "$100,000,000"


def test_seerr_skips_omdb_without_api_key():
    discover = {"results": [{"id": 101, "title": "No Key", "mediaType": "movie", "voteAverage": 5}]}
    detail = {"imdbId": "tt1111111"}
    client = FakeClient(discover, by_url={"/api/v1/movie/101": detail})
    item = SeerrProvider(url="http://seerr:5055", api_key="k", client=client).list_items()[0]
    assert item.imdb_id == "tt1111111"
    assert item.imdb_rating is None


def test_jellyfin_partial_and_watched():
    payload = {
        "Items": [
            {
                "Id": "p1",
                "Name": "Mid-credit",
                "UserData": {"Played": False, "PlaybackPositionTicks": 50_000_000},
            },
            {
                "Id": "w1",
                "Name": "Finished",
                "UserData": {"Played": True, "PlaybackPositionTicks": 0},
            },
        ]
    }
    items = JellyfinProvider(url="http://jf:8096", api_key="k", user_id="u", client=FakeClient(payload)).list_items()
    states = {item.title: item.watch_state for item in items}
    assert states["Mid-credit"] == "partial"
    assert states["Finished"] == "watched"


def test_demo_items_have_bundled_stills():
    from pathlib import Path

    from app.demo_art import load_catalog, still_path_for_item
    from app.providers.demo import DemoProvider

    catalog = load_catalog()
    assert len(catalog) == 6
    items = DemoProvider().list_items()
    assert len(items) == 6
    for item in items:
        path = still_path_for_item(item)
        assert path is not None, item.title
        assert Path(item.backdrop_path).is_file()
        assert Path(item.backdrop_path).stat().st_size > 20_000
    north = next(item for item in items if item.title == "Northlight")
    assert north.logo_url
    harbor = next(item for item in items if item.title == "Harbor Season")
    assert not harbor.logo_url


def test_looks_like_image_rejects_html_and_wav():
    from app.images import looks_like_image

    assert looks_like_image(b"\xff\xd8\xff" + b"\x00" * 8)
    assert not looks_like_image(b"<!DOCTYPE html>")
    assert not looks_like_image(b"RIFF" + b"\x00" * 4 + b"WAVE")
    assert looks_like_image(b"RIFF" + b"\x00" * 4 + b"WEBP")


def test_unconfigured_providers_do_not_call_network():
    assert JellyfinProvider().test()["ok"] is False
    assert SeerrProvider().test()["ok"] is False
    assert TmdbProvider().test()["ok"] is False
    assert JellyfinProvider().list_items() == []
    assert SeerrProvider().list_items() == []
    assert DemoProvider().test()["ok"] is True


def test_seerr_test_uses_auth_me_not_public_status():
    """``/api/v1/status`` is public; a real key check must hit ``/api/v1/auth/me``."""

    class Client:
        def __init__(self):
            self.urls: list[str] = []

        def get_json(self, url, headers=None, params=None):
            self.urls.append(url)
            assert headers and headers.get("X-Api-Key") == "secret"
            assert headers.get("Authorization") == "Bearer secret"
            if url.endswith("/auth/me"):
                return {"id": 1, "displayName": "Admin", "email": "a@b.c"}
            if url.endswith("/status"):
                return {"version": "3.4.1"}
            raise AssertionError(f"unexpected url {url}")

    client = Client()
    out = SeerrProvider(url="http://seerr:5055", api_key="  Bearer secret  ", client=client).test()
    assert out["ok"] is True
    assert out["server"] == "3.4.1"
    assert any(u.endswith("/auth/me") for u in client.urls)
    assert client.urls[0].endswith("/auth/me")


def test_seerr_test_rejects_bad_api_key():
    import httpx

    class Client:
        def get_json(self, url, headers=None, params=None):
            request = httpx.Request("GET", url)
            response = httpx.Response(403, request=request, json={"error": "forbidden"})
            raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    out = SeerrProvider(url="http://seerr:5055", api_key="bad", client=Client()).test()
    assert out["ok"] is False
    assert "API key" in out["error"]


def test_seerr_strips_bearer_prefix_and_sends_both_headers():
    seen: dict = {}

    class Client:
        def get_json(self, url, headers=None, params=None):
            seen["headers"] = headers
            return {"results": []}

    SeerrProvider(url="http://seerr:5055", api_key="Bearer abc.def", client=Client()).list_items()
    assert seen["headers"]["X-Api-Key"] == "abc.def"
    assert seen["headers"]["Authorization"] == "Bearer abc.def"


def test_tmdb_enrich_fills_missing_artwork():
    class Client:
        def get_json(self, url, headers=None, params=None):
            return {
                "id": 42,
                "overview": "Enriched",
                "vote_average": 8.1,
                "genres": [{"name": "Sci-Fi"}],
                "backdrop_path": "/back.jpg",
                "poster_path": "/poster.jpg",
            }

    item = MediaItem(title="Probe", tmdb_id="42")
    out = TmdbProvider(api_key="k", client=Client()).enrich(item)
    assert out.overview == "Enriched"
    assert out.backdrop_url.endswith("/back.jpg")
    assert out.poster_url.endswith("/poster.jpg")
    skipped = TmdbProvider(api_key="").enrich(item)
    assert skipped.overview == ""


def test_tmdb_selects_english_png_logo():
    from app.providers.tmdb import logo_image_url, select_logo_path

    path = select_logo_path(
        {
            "logos": [
                {"file_path": "/ja.jpg", "iso_639_1": "ja", "vote_average": 9},
                {"file_path": "/en.png", "iso_639_1": "en", "vote_average": 1},
                {"file_path": "/plain.png", "iso_639_1": None, "vote_average": 8},
            ]
        },
        language="en-US",
    )
    assert path == "/en.png"
    assert logo_image_url(path) == "https://image.tmdb.org/t/p/original/en.png"


def test_tmdb_enrich_fetches_logo_from_images_api():
    class Client:
        def get_json(self, url, headers=None, params=None):
            if "/images" in url:
                assert "include_image_language" in (params or {})
                return {"logos": [{"file_path": "/mark.png", "iso_639_1": "en", "vote_average": 5}]}
            return {"id": 42, "overview": "Enriched", "vote_average": 8.1, "genres": [], "backdrop_path": "/b.jpg"}

    out = TmdbProvider(api_key="k", client=Client()).enrich(MediaItem(title="Probe", tmdb_id="42"))
    assert out.logo_url == "https://image.tmdb.org/t/p/original/mark.png"


def test_tmdb_logo_fetch_survives_missing_payload():
    class Client:
        def get_json(self, url, headers=None, params=None):
            raise RuntimeError("nope")

    assert TmdbProvider(api_key="k", client=Client()).fetch_logo_url("1", "movie") is None


def test_jellyfin_uses_primary_when_no_backdrop_tag():
    payload = {
        "Items": [
            {
                "Id": "poster-only",
                "Name": "Still",
                "ImageTags": {"Primary": "aaa"},
                "BackdropImageTags": [],
            }
        ]
    }
    item = JellyfinProvider(url="http://jf:8096", api_key="k", user_id="u", client=FakeClient(payload)).list_items()[0]
    assert item.backdrop_url == "http://jf:8096/Items/poster-only/Images/Primary?maxWidth=1920"
    assert item.poster_url == "http://jf:8096/Items/poster-only/Images/Primary?maxHeight=600"
    assert item.logo_url is None


def test_jellyfin_logo_tag_builds_logo_url():
    payload = {
        "Items": [
            {
                "Id": "with-logo",
                "Name": "Marked",
                "ImageTags": {"Primary": "p", "Logo": "lg"},
                "BackdropImageTags": ["b"],
            }
        ]
    }
    item = JellyfinProvider(url="http://jf:8096", api_key="k", user_id="u", client=FakeClient(payload)).list_items()[0]
    assert item.logo_url == "http://jf:8096/Items/with-logo/Images/Logo"
    assert item.backdrop_url == "http://jf:8096/Items/with-logo/Images/Backdrop?maxWidth=1920"
