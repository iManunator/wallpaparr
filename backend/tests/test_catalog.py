"""Catalog path safety and corrupt JSON recovery."""

from __future__ import annotations

import json
from pathlib import Path

from app.models import AppSettings, WallpaperRecord


def test_wallpaper_file_rejects_path_traversal(suite_dirs):
    catalog_mod = suite_dirs["catalog_mod"]
    gallery: Path = suite_dirs["gallery"]
    layout = gallery / "Netflix Hero"
    layout.mkdir(parents=True, exist_ok=True)
    (layout / "northlight.jpg").write_bytes(b"\xff\xd8\xff")
    # Sibling folder whose name is a prefix-plus-suffix of the layout dir —
    # the old str.startswith check treated this as inside "Netflix Hero".
    extra = gallery / "Netflix Hero-extra"
    extra.mkdir()
    (extra / "stolen.jpg").write_bytes(b"secret")
    assert catalog_mod.wallpaper_file("Netflix Hero", "../Netflix Hero-extra/stolen.jpg") is None
    assert catalog_mod.wallpaper_file("Netflix Hero", "northlight.jpg") is not None


def test_wallpaper_image_does_not_create_missing_layout_dir(client, suite_dirs):
    gallery: Path = suite_dirs["gallery"]
    response = client.get("/api/wallpaper/image/Does Not Exist/foo.jpg")
    assert response.status_code == 404
    assert not (gallery / "Does Not Exist").exists()


def test_load_catalog_skips_corrupt_file_and_bad_rows(suite_dirs):
    catalog_mod = suite_dirs["catalog_mod"]
    from app.config import CATALOG_PATH

    CATALOG_PATH.write_text("{not-json", encoding="utf-8")
    assert catalog_mod.load_catalog() == []
    assert CATALOG_PATH.read_text(encoding="utf-8") == "{not-json"

    good = WallpaperRecord(
        id="ok",
        layout="Netflix Hero",
        filename="northlight.jpg",
        title="Northlight",
    )
    catalog_mod.save_catalog([good])
    mixed = [good.model_dump(), {"id": 1}]
    CATALOG_PATH.write_text(json.dumps(mixed), encoding="utf-8")
    loaded = catalog_mod.load_catalog()
    assert [item.id for item in loaded] == ["ok"]


def test_load_settings_survives_corrupt_json(suite_dirs):
    from app.config import CONFIG_PATH, load_settings

    CONFIG_PATH.write_text("{broken", encoding="utf-8")
    settings = load_settings()
    assert isinstance(settings, AppSettings)
    assert CONFIG_PATH.read_text(encoding="utf-8") == "{broken"


def test_config_example_tracks_app_settings_defaults():
    raw = json.loads((Path(__file__).resolve().parents[2] / "config.example.json").read_text(encoding="utf-8"))
    example = AppSettings.model_validate(raw)
    defaults = AppSettings()
    assert example.motion_preset == defaults.motion_preset
    assert example.motion_fps == defaults.motion_fps
    assert example.motion_duration == defaults.motion_duration
    assert example.taste_weights == defaults.taste_weights
    assert example.motion_edge_fade == defaults.motion_edge_fade
    assert example.motion_fly_in == defaults.motion_fly_in
    assert "api_key" in example.omdb
