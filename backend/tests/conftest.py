"""Pytest fixtures: isolated data dir, seeded catalog, FastAPI client."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# Isolate all suite paths before importing the app.
ROOT = Path(__file__).resolve().parent / "_tmp_data"


@pytest.fixture()
def suite_dirs(tmp_path, monkeypatch):
    data = tmp_path / "data"
    layouts = tmp_path / "layouts"
    gallery = data / "gallery"
    monkeypatch.setenv("SUITE_DATA", str(data))
    monkeypatch.setenv("SUITE_LAYOUTS", str(layouts))
    monkeypatch.setenv("SUITE_GALLERY", str(gallery))
    monkeypatch.setenv("SUITE_CONFIG", str(data / "config.json"))
    monkeypatch.setenv("SUITE_CATALOG", str(data / "catalog.json"))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://testserver")
    monkeypatch.setenv("SUITE_SKIP_SEED", "1")
    monkeypatch.setenv("SUITE_SKIP_SCHEDULER", "1")
    # Re-import config-backed modules with the patched env.
    import importlib

    import app.api as api_mod
    import app.catalog as catalog_mod
    import app.config as config_mod
    import app.generate as generate_mod
    import app.jobs as jobs_mod
    import app.layouts as layouts_mod
    import app.main as main_mod
    import app.ops as ops_mod
    import app.progress as progress_mod

    importlib.reload(config_mod)
    importlib.reload(catalog_mod)
    importlib.reload(layouts_mod)
    importlib.reload(generate_mod)
    importlib.reload(jobs_mod)
    importlib.reload(ops_mod)
    importlib.reload(api_mod)
    importlib.reload(main_mod)
    progress_mod.reset_for_tests()
    config_mod.ensure_dirs()
    layouts_mod.seed_presets()
    return {
        "data": data,
        "layouts": layouts,
        "gallery": gallery,
        "catalog_mod": catalog_mod,
        "layouts_mod": layouts_mod,
        "main_mod": main_mod,
    }


def _write_jpg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 36), (20, 30, 50)).save(path, "JPEG")


@pytest.fixture()
def seeded_catalog(suite_dirs):
    from app.models import WallpaperRecord

    catalog_mod = suite_dirs["catalog_mod"]
    gallery = suite_dirs["gallery"]
    now = time.time()
    records = [
        WallpaperRecord(
            id="1",
            layout="Netflix Hero",
            filename="northlight.jpg",
            title="Northlight",
            year=2024,
            rating=8.4,
            genres=["Sci-Fi", "Mystery"],
            official_rating="PG-13",
            watch_state="unwatched",
            library_state="in_library",
            availability="available",
            source="jellyfin",
            jellyfin_id="demo-jf-1",
            tmdb_id="90001",
            action_url="jellyfin://items/demo-jf-1",
            mtime=now,
        ),
        WallpaperRecord(
            id="2",
            layout="Netflix Hero",
            filename="harbor.jpg",
            title="Harbor Season",
            year=2022,
            rating=7.9,
            genres=["Drama"],
            official_rating="TV-14",
            watch_state="partial",
            library_state="in_library",
            availability="available",
            source="jellyfin",
            jellyfin_id="demo-jf-2",
            action_url="jellyfin://items/demo-jf-2",
            mtime=now - 100,
        ),
        WallpaperRecord(
            id="3",
            layout="Netflix Hero",
            filename="glass.jpg",
            title="Glass Orchard",
            year=2018,
            rating=8.1,
            genres=["Fantasy", "Drama"],
            official_rating="PG",
            watch_state="watched",
            library_state="in_library",
            availability="available",
            source="jellyfin",
            jellyfin_id="demo-jf-3",
            mtime=now - 200,
        ),
        WallpaperRecord(
            id="4",
            layout="Prime Cinematic",
            filename="signal.jpg",
            title="Signal Country",
            year=2023,
            rating=7.6,
            genres=["Thriller", "Sci-Fi"],
            official_rating="TV-MA",
            watch_state="unwatched",
            library_state="seerr_only",
            availability="requestable",
            source="jellyseerr",
            tmdb_id="90004",
            mtime=now - 50,
        ),
        WallpaperRecord(
            id="5",
            layout="Prime Cinematic",
            filename="atlas.jpg",
            title="Paper Atlas",
            year=1999,
            rating=6.4,
            genres=["Adventure", "Comedy"],
            official_rating="PG",
            watch_state="watched",
            library_state="in_library",
            availability="available",
            source="plex",
            imdb_id="tt9000005",
            mtime=now - 400,
        ),
        WallpaperRecord(
            id="6",
            layout="Prime Cinematic",
            filename="relay.jpg",
            title="Night Relay",
            year=2021,
            rating=8.7,
            genres=["Action", "Sci-Fi"],
            official_rating="PG-13",
            watch_state="unwatched",
            library_state="in_library",
            availability="available",
            source="jellyseerr",
            jellyfin_id="demo-jf-6",
            tmdb_id="90006",
            action_url="jellyfin://items/demo-jf-6",
            mtime=now - 10,
            has_video=True,
        ),
    ]
    for rec in records:
        _write_jpg(gallery / rec.layout / rec.filename)
        if rec.has_video:
            mp4 = gallery / rec.layout / rec.filename
            mp4.with_suffix(".mp4").write_bytes(b"\x00" * 1500)
    catalog_mod.save_catalog(records)
    return records


@pytest.fixture()
def client(suite_dirs, seeded_catalog, monkeypatch):
    main_mod = suite_dirs["main_mod"]
    # Avoid demo auto-seed and scheduler side effects during tests.
    monkeypatch.setattr(main_mod, "start_scheduler", lambda: None)
    monkeypatch.setattr(main_mod, "shutdown_scheduler", lambda: None)
    from app.progress import reset_for_tests

    reset_for_tests()

    with TestClient(main_mod.app) as test_client:
        yield test_client
