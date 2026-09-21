"""Batch generate must download provider artwork, not only paint metadata."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.models import GenerateRequest, MediaItem


def _jpeg(color: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (320, 180), color).save(buf, "JPEG", quality=95)
    return buf.getvalue()


def test_generate_one_paints_downloaded_backdrop(suite_dirs):
    from app.generate import generate_one

    jpeg = _jpeg((220, 30, 30))
    called: list[str] = []

    def http_get(url: str) -> bytes:
        called.append(url)
        return jpeg

    item = MediaItem(
        title="Red Planet",
        year=2024,
        overview="Dust.",
        genres=["Sci-Fi"],
        backdrop_url="http://jf:8096/Items/1/Images/Backdrop?maxWidth=1920",
        jellyfin_id="1",
        source="jellyfin",
    )
    record = generate_one(item, "Netflix Hero", http_get=http_get)
    assert record is not None
    assert called == [item.backdrop_url]
    path = suite_dirs["gallery"] / "Netflix Hero" / record.filename
    pixel = Image.open(path).getpixel((1500, 420))
    assert pixel[0] > 80
    assert pixel[0] > pixel[2]


def test_generate_one_falls_back_to_poster(suite_dirs):
    from app.generate import generate_one

    jpeg = _jpeg((20, 180, 40))
    called: list[str] = []

    def http_get(url: str) -> bytes:
        called.append(url)
        if "Backdrop" in url:
            raise RuntimeError("no backdrop")
        return jpeg

    item = MediaItem(
        title="Green Room",
        backdrop_url="http://jf:8096/Items/2/Images/Backdrop?maxWidth=1920",
        poster_url="http://jf:8096/Items/2/Images/Primary?maxHeight=600",
        jellyfin_id="2",
        source="jellyfin",
    )
    record = generate_one(item, "Netflix Hero", http_get=http_get)
    assert record is not None
    assert called == [item.backdrop_url, item.poster_url]
    pixel = Image.open(suite_dirs["gallery"] / "Netflix Hero" / record.filename).getpixel((1500, 420))
    assert pixel[1] > 70


def test_run_generate_downloads_without_injected_client(suite_dirs, monkeypatch):
    from app import generate as generate_mod
    from app.models import MediaItem as Item

    jpeg = _jpeg((30, 40, 210))
    monkeypatch.setattr(generate_mod, "_default_http_get", lambda url: jpeg)
    monkeypatch.setattr(
        generate_mod,
        "collect_items",
        lambda source, limit, warnings=None, seerr_category=None: [
            Item(
                title="Silo",
                year=2023,
                backdrop_url="http://jf:8096/Items/silo/Images/Backdrop",
                jellyfin_id="silo",
                source="jellyfin",
            )
        ],
    )
    out = generate_mod.run_generate(GenerateRequest(source="jellyfin", layout="Netflix Hero", limit=1, skip_existing=False))
    assert out["count"] == 1
    assert out["created"] == ["Silo"]
    files = list((suite_dirs["gallery"] / "Netflix Hero").glob("silo-*.jpg"))
    assert files
    pixel = Image.open(files[0]).getpixel((1500, 420))
    assert pixel[2] > 80


def _png_logo(color=(255, 220, 40, 255)) -> bytes:
    buf = io.BytesIO()
    image = Image.new("RGBA", (640, 160), (0, 0, 0, 0))
    image.paste(color, (8, 8, 632, 152))
    image.save(buf, "PNG")
    return buf.getvalue()


def test_generate_one_composites_logo_instead_of_title(suite_dirs):
    from app.generate import generate_one

    jpeg = _jpeg((12, 14, 18))
    png = _png_logo()

    def http_get(url: str) -> bytes:
        if "Logo" in url:
            return png
        return jpeg

    item = MediaItem(
        title="UNIQUE_TITLE_GLYPH",
        year=2024,
        genres=["Drama"],
        backdrop_url="http://jf:8096/Items/9/Images/Backdrop?maxWidth=1920",
        logo_url="http://jf:8096/Items/9/Images/Logo",
        jellyfin_id="9",
        source="jellyfin",
    )
    record = generate_one(item, "Netflix Hero", http_get=http_get)
    assert record is not None
    pixel = Image.open(suite_dirs["gallery"] / "Netflix Hero" / record.filename).getpixel((120, 100))
    assert pixel[0] > 180
    assert pixel[1] > 140
    assert pixel[0] > pixel[2]


def test_default_http_get_sends_jellyfin_auth(suite_dirs, monkeypatch):
    from app.config import save_settings
    from app.generate import _default_http_get
    from app.models import AppSettings

    save_settings(AppSettings(jellyfin={"url": "http://jf:8096", "api_key": "secret", "user_id": "u"}))
    seen: dict = {}

    class Client:
        def __init__(self, timeout: float = 15.0):
            self.timeout = timeout

        def get_bytes(self, url, headers=None):
            seen["url"] = url
            seen["headers"] = headers
            return b"\xff\xd8\xff" + b"\x00" * 16

    monkeypatch.setattr("app.generate.HttpClient", Client)
    data = _default_http_get("http://jf:8096/Items/1/Images/Backdrop")
    assert data.startswith(b"\xff\xd8\xff")
    assert seen["headers"]["Authorization"].startswith("MediaBrowser")
    assert "secret" in seen["headers"]["Authorization"]
    assert seen["headers"]["X-Emby-Token"] == "secret"


def test_fetch_artwork_rejects_html(suite_dirs):
    from app.generate import _fetch_artwork
    from app.models import MediaItem

    item = MediaItem(
        title="From",
        backdrop_url="http://jf:8096/Items/x/Images/Backdrop",
        jellyfin_id="real-1",
        source="jellyfin",
    )
    data = _fetch_artwork(item, http_get=lambda url: b"<!DOCTYPE html><html>nope</html>")
    assert data is None


def test_jellyfin_unconfigured_generate_warns_and_uses_demo(suite_dirs):
    from app.generate import run_generate
    from app.models import GenerateRequest

    out = run_generate(GenerateRequest(source="jellyfin", layout="Netflix Hero", limit=1, skip_existing=False))
    assert out["count"] == 1
    assert out["created"]
    assert any("Jellyfin is not configured" in w for w in out["warnings"])
    assert "Created 1 still" in out["message"]


def test_generate_one_uses_bundled_demo_still(suite_dirs):
    from app.generate import generate_one
    from app.providers.demo import DemoProvider
    from app.render import synthetic_backdrop
    from PIL import Image

    item = DemoProvider().list_items()[0]
    record = generate_one(item, "Netflix Hero")
    path = suite_dirs["gallery"] / "Netflix Hero" / record.filename
    painted = Image.open(path)
    synth = synthetic_backdrop(item.title, painted.size)
    assert painted.getpixel((1500, 360)) != synth.getpixel((1500, 360))


def test_bake_motion_uses_source_artwork_not_composite(suite_dirs, monkeypatch):
    from app import generate as generate_mod
    from app.generate import bake_motion, generate_one
    from app.models import MediaItem

    item = MediaItem(
        title="Northlight",
        year=2024,
        overview="Maps.",
        rating=8.4,
        genres=["Sci-Fi"],
        jellyfin_id="demo-jf-1",
        source="demo",
    )
    record = generate_one(item, "Netflix Hero", motion=False)
    jpg = suite_dirs["gallery"] / "Netflix Hero" / record.filename
    composite = jpg.read_bytes()
    captured: dict = {}
    real_plate = generate_mod.render_plate

    def spy(media, layout, backdrop_bytes=None):
        captured["bytes"] = backdrop_bytes
        return real_plate(media, layout, backdrop_bytes=backdrop_bytes)

    monkeypatch.setattr(generate_mod, "render_plate", spy)
    monkeypatch.setattr(generate_mod, "generate_motion", lambda *a, **k: (True, "ok"))
    monkeypatch.setattr(generate_mod, "has_motion", lambda p: True)
    out = bake_motion("Netflix Hero", record.filename)
    assert out["layered"] is True
    assert out["chrome_locked"] is True
    assert captured.get("bytes")
    assert captured["bytes"] != composite


def test_generate_one_motion_puts_atmosphere_on_chrome_not_plate(suite_dirs, monkeypatch):
    """Batch VIDEO must Ken-Burns artwork only; vignette/letterbox live on chrome."""
    from app import generate as generate_mod
    from app.config import save_settings
    from app.generate import generate_one
    from app.models import AppSettings, MediaItem
    from PIL import Image

    save_settings(AppSettings(motion_style="parallax", motion_preset="bold", light_leak=True, motion_duration=2))
    captured: dict = {}

    def spy(jpg, **kwargs):
        captured["plate"] = Image.open(kwargs["plate"]).convert("RGB") if kwargs.get("plate") else None
        captured["chrome"] = Image.open(kwargs["chrome"]).convert("RGBA") if kwargs.get("chrome") else None
        captured["still"] = Image.open(jpg).convert("RGB")
        return True, "ok"

    monkeypatch.setattr(generate_mod, "generate_motion", spy)
    monkeypatch.setattr(generate_mod, "has_motion", lambda p: True)

    jpeg = _jpeg((220, 40, 30))
    item = MediaItem(
        title="Red Planet",
        year=2024,
        backdrop_url="http://jf:8096/Items/1/Images/Backdrop?maxWidth=1920",
        jellyfin_id="1",
        source="jellyfin",
    )
    record = generate_one(item, "Netflix Hero", motion=True, http_get=lambda url: jpeg)
    assert record is not None
    assert captured["plate"] is not None
    assert captured["chrome"] is not None
    plate_corner = captured["plate"].getpixel((4, 4))
    still_corner = captured["still"].getpixel((4, 4))
    chrome_corner = captured["chrome"].getpixel((4, 4))
    assert plate_corner[0] > 150
    assert still_corner[0] < plate_corner[0]
    assert chrome_corner[3] == 255


def test_bake_motion_one_tap_locks_atmosphere_on_chrome(suite_dirs, monkeypatch):
    from app import generate as generate_mod
    from app.generate import bake_motion, generate_one
    from app.models import MediaItem
    from PIL import Image

    item = MediaItem(
        title="Harbor Season",
        year=2022,
        jellyfin_id="demo-jf-2",
        source="demo",
    )
    record = generate_one(item, "Netflix Hero", motion=False)
    captured: dict = {}

    def spy(jpg, **kwargs):
        captured["chrome"] = Image.open(kwargs["chrome"]).convert("RGBA") if kwargs.get("chrome") else None
        captured["plate"] = Image.open(kwargs["plate"]).convert("RGB") if kwargs.get("plate") else None
        return True, "ok"

    monkeypatch.setattr(generate_mod, "generate_motion", spy)
    monkeypatch.setattr(generate_mod, "has_motion", lambda p: True)
    out = bake_motion("Netflix Hero", record.filename)
    assert out["chrome_locked"] is True
    assert captured["chrome"] is not None
    assert captured["chrome"].getpixel((4, 4))[3] == 255
    assert captured["plate"].getpixel((4, 4))[0] > captured["chrome"].getpixel((4, 4))[0]


def test_bake_motion_stable_when_vary_off(suite_dirs, monkeypatch):
    from app import generate as generate_mod
    from app.config import save_settings
    from app.generate import bake_motion, generate_one
    from app.models import AppSettings, MediaItem

    save_settings(AppSettings(motion_vary=False, motion_preset="cinematic", motion_duration=2))
    profiles = []

    def spy(jpg, **kwargs):
        profiles.append(kwargs.get("profile"))
        return True, "ok"

    monkeypatch.setattr(generate_mod, "generate_motion", spy)
    monkeypatch.setattr(generate_mod, "has_motion", lambda p: True)
    first = generate_one(
        MediaItem(title="Northlight", year=2024, jellyfin_id="demo-jf-1", source="demo"),
        "Netflix Hero",
        motion=False,
    )
    second = generate_one(
        MediaItem(title="Harbor Season", year=2022, jellyfin_id="demo-jf-2", source="demo"),
        "Netflix Hero",
        motion=False,
    )
    bake_motion("Netflix Hero", first.filename)
    bake_motion("Netflix Hero", second.filename)
    assert len(profiles) == 2
    assert profiles[0].intensity == profiles[1].intensity
    assert profiles[0].pan_x_sign == profiles[1].pan_x_sign == 1
    assert profiles[0].phase == profiles[1].phase == 0
    assert profiles[0].zoom_scale == profiles[1].zoom_scale == 1


def test_bake_motion_varies_per_title_when_enabled(suite_dirs, monkeypatch):
    from app import generate as generate_mod
    from app.config import save_settings
    from app.generate import bake_motion, generate_one
    from app.models import AppSettings, MediaItem

    save_settings(AppSettings(motion_vary=True, motion_preset="cinematic", motion_duration=2))
    profiles = []

    def spy(jpg, **kwargs):
        profiles.append(kwargs.get("profile"))
        return True, "ok"

    monkeypatch.setattr(generate_mod, "generate_motion", spy)
    monkeypatch.setattr(generate_mod, "has_motion", lambda p: True)
    first = generate_one(
        MediaItem(title="Northlight", year=2024, jellyfin_id="demo-jf-1", source="demo"),
        "Netflix Hero",
        motion=False,
    )
    second = generate_one(
        MediaItem(title="Harbor Season", year=2022, jellyfin_id="demo-jf-2", source="demo"),
        "Netflix Hero",
        motion=False,
    )
    out = bake_motion("Netflix Hero", first.filename)
    bake_motion("Netflix Hero", first.filename)
    bake_motion("Netflix Hero", second.filename)
    assert out["vary"] is True
    assert len(profiles) == 3
    assert profiles[0] == profiles[1]
    assert profiles[0] != profiles[2]
    assert 0.40 <= profiles[0].intensity <= 0.72
    assert 0.40 <= profiles[2].intensity <= 0.72
    assert profiles[0].fg_pan == 0
    assert profiles[2].fg_pan == 0


def test_run_generate_refreshes_when_status_changes(suite_dirs, monkeypatch):
    from app import catalog as catalog_store
    from app import generate as generate_mod
    from app.generate import run_generate
    from app.models import GenerateRequest, MediaItem, WallpaperRecord

    catalog_store.upsert(
        WallpaperRecord(
            id="old",
            layout="Netflix Hero",
            filename="old.jpg",
            title="Show",
            jellyfin_id="jf-9",
            watch_state="unwatched",
            availability="requestable",
            library_state="seerr_only",
            source="jellyseerr",
        )
    )
    item = MediaItem(
        title="Show",
        jellyfin_id="jf-9",
        watch_state="watched",
        availability="available",
        library_state="in_library",
        source="jellyfin",
    )
    calls = []

    def fake_one(media, layout, motion=False, replace=False, http_get=None):
        calls.append({"replace": replace, "watch": media.watch_state})
        return WallpaperRecord(
            id="new",
            layout=layout,
            filename="new.jpg",
            title=media.title,
            jellyfin_id=media.jellyfin_id,
            watch_state=media.watch_state,
            availability=media.availability,
            library_state=media.library_state,
            source=media.source,
        )

    monkeypatch.setattr(generate_mod, "collect_items", lambda *a, **k: [item])
    monkeypatch.setattr(generate_mod, "generate_one", fake_one)

    skipped = run_generate(
        GenerateRequest(layout="Netflix Hero", source="jellyfin", limit=1, skip_existing=True, refresh_status=False)
    )
    assert skipped["skipped"] == ["Show"]
    assert calls == []

    refreshed = run_generate(
        GenerateRequest(layout="Netflix Hero", source="jellyfin", limit=1, skip_existing=True, refresh_status=True)
    )
    assert refreshed["refreshed"] == ["Show"]
    assert refreshed["created"] == ["Show"]
    assert calls == [{"replace": True, "watch": "watched"}]


def test_headers_for_url_requires_same_origin(suite_dirs):
    from app.config import save_settings
    from app.generate import _headers_for_url
    from app.models import AppSettings

    save_settings(AppSettings(jellyfin={"url": "http://jf:8096", "api_key": "secret", "user_id": "u"}))
    assert _headers_for_url("http://jf:8096/Items/1/Images/Backdrop") is not None
    assert _headers_for_url("http://jf:8096.evil.example/Items/1/Images/Backdrop") is None
    assert _headers_for_url("http://jf:80960/Items/1/Images/Backdrop") is None
    assert _headers_for_url("https://jf:8096/Items/1/Images/Backdrop") is None
    assert _headers_for_url("file:///etc/passwd") is None


def test_generate_one_keeps_previous_still_if_render_fails(suite_dirs, monkeypatch):
    from app import generate as generate_mod
    from app.generate import generate_one
    from app.models import MediaItem, WallpaperRecord

    catalog_mod = suite_dirs["catalog_mod"]
    dest_dir = suite_dirs["gallery"] / "Netflix Hero"
    dest_dir.mkdir(parents=True, exist_ok=True)
    jpg = dest_dir / "keep-me-jf-keep.jpg"
    jpg.write_bytes(b"\xff\xd8\xff" + b"\x00" * 32)
    catalog_mod.upsert(
        WallpaperRecord(
            id="old",
            layout="Netflix Hero",
            filename=jpg.name,
            title="Keep Me",
            jellyfin_id="jf-keep",
        )
    )

    def boom(*_args, **_kwargs):
        raise RuntimeError("paint failed")

    monkeypatch.setattr(generate_mod, "render_still", boom)
    item = MediaItem(title="Keep Me", jellyfin_id="jf-keep", source="jellyfin")
    with pytest.raises(RuntimeError, match="paint failed"):
        generate_one(item, "Netflix Hero", http_get=lambda _url: _jpeg((10, 10, 10)))
    assert jpg.is_file()
    assert any(rec.id == "old" for rec in catalog_mod.load_catalog())


def test_still_only_replace_removes_stale_mp4(suite_dirs):
    from app.generate import _filename_for, generate_one
    from app.models import MediaItem, WallpaperRecord

    catalog_mod = suite_dirs["catalog_mod"]
    item = MediaItem(title="Stale Loop", jellyfin_id="jf-stale", source="jellyfin")
    filename = _filename_for(item)
    dest_dir = suite_dirs["gallery"] / "Netflix Hero"
    dest_dir.mkdir(parents=True, exist_ok=True)
    jpg = dest_dir / filename
    jpg.write_bytes(b"\xff\xd8\xff" + b"\x00" * 32)
    mp4 = jpg.with_suffix(".mp4")
    mp4.write_bytes(b"\x00" * 1500)
    catalog_mod.upsert(
        WallpaperRecord(
            id="old-loop",
            layout="Netflix Hero",
            filename=filename,
            title=item.title,
            jellyfin_id=item.jellyfin_id,
            has_video=True,
        )
    )
    record = generate_one(item, "Netflix Hero", motion=False, http_get=lambda _url: _jpeg((12, 14, 18)))
    assert record is not None
    assert not mp4.exists()
    assert record.has_video is False
    rows = [rec for rec in catalog_mod.load_catalog() if rec.jellyfin_id == "jf-stale"]
    assert len(rows) == 1


def test_regenerate_does_not_duplicate_catalog_rows(suite_dirs):
    from app.generate import generate_one
    from app.models import MediaItem

    item = MediaItem(
        title="Once",
        jellyfin_id="jf-once",
        source="jellyfin",
        backdrop_url="http://jf:8096/Items/jf-once/Images/Backdrop",
    )
    jpeg = _jpeg((30, 30, 30))
    first = generate_one(item, "Netflix Hero", http_get=lambda _url: jpeg)
    second = generate_one(item, "Netflix Hero", http_get=lambda _url: jpeg, replace=False)
    assert first is not None and second is not None
    from app.catalog import load_catalog

    rows = [rec for rec in load_catalog() if rec.jellyfin_id == "jf-once"]
    assert len(rows) == 1

