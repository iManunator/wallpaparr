from __future__ import annotations

import json

from app.layout_geometry import (
    MIN_GAP,
    NETFLIX_GOLD,
    SAMPLE,
    box_outside_safe,
    chrome_boxes,
    collisions,
    overview_max_lines,
)
from app.layouts import DNA_REVISION, PRESETS
from app.logo import PADDING, SAFE_BOTTOM, SAFE_LEFT, logo_max_box
from app.models import MediaItem
from app.render import render_chrome, render_still


DNA_NAMES = (
    "Netflix Hero",
    "Prime Cinematic",
    "Google TV Clean",
    "Status Focus",
    "Jellyfin Dense",
    "Projectivy Dock",
)

PROBE = MediaItem(
    title=SAMPLE["title"],
    year=2024,
    overview=SAMPLE["overview"],
    rating=8.4,
    genres=["Sci-Fi", "Mystery", "Drama", "Thriller", "Adventure"],
    official_rating="PG-13",
    runtime="2h 11m",
    watch_state="unwatched",
    library_state="seerr_only",
    availability="requestable",
    source="jellyseerr",
)


def _layer(layout, slot: str):
    return next(layer for layer in layout.layers if layer.slot == slot)


def test_bundled_preset_names_match_layout_dna():
    assert tuple(PRESETS) == DNA_NAMES


def test_netflix_hero_gold_reference_is_unchanged():
    layout = PRESETS["Netflix Hero"]
    assert layout.title_display == "auto"
    assert layout.logo_padding == PADDING
    for slot, expected in NETFLIX_GOLD.items():
        layer = _layer(layout, slot)
        for key, value in expected.items():
            assert getattr(layer, key) == value, (slot, key)


def test_every_preset_has_runtime_slot():
    for name, layout in PRESETS.items():
        runtime = _layer(layout, "runtime")
        assert runtime.visible, name
        assert runtime.font_size >= 20, name


def test_every_preset_has_tv_safe_watch_row_and_logo_slot():
    for name, layout in PRESETS.items():
        assert layout.dna_revision == DNA_REVISION, name
        assert layout.title_display == "auto", name
        assert layout.show_watch_badge is True, name
        assert layout.show_seerr_badge is True, name
        title = _layer(layout, "title")
        assert title.width and title.height, name
        assert title.x >= SAFE_LEFT, name
        assert title.y >= 64, name
        watch = _layer(layout, "watch_status")
        # Seerr sits on the watch row — nothing else may share that band.
        for layer in layout.layers:
            if layer.slot in ("watch_status", "watch_state", "seerr_status", "seerr_state"):
                continue
            if abs(layer.y - watch.y) < 20:
                raise AssertionError(f"{name}: {layer.slot} shares the watch/Seerr row")
        first_meta = min(
            (layer.y for layer in layout.layers if layer.visible and layer.slot != "title" and layer.y > title.y),
            default=None,
        )
        if first_meta is not None:
            # Logo uses the title box; Netflix is the tight gold (70+130+25 vs 220).
            assert title.y + title.height + PADDING <= first_meta + 8, name


def test_preset_chrome_stays_in_safe_zones_without_collisions():
    for name, layout in PRESETS.items():
        boxes = chrome_boxes(layout)
        hits = collisions(boxes, gap=MIN_GAP)
        assert hits == [], f"{name} overlaps {hits}"
        for box in boxes:
            assert not box_outside_safe(box, layout), f"{name} {box.id} {box}"
        seerr = next(box for box in boxes if box.slot in ("seerr_status", "seerr_state"))
        assert seerr.x1 <= layout.canvas_width - 72, name
        bottom = max(box.y1 for box in boxes)
        assert bottom <= layout.canvas_height - SAFE_BOTTOM, name


def test_projectivy_dock_sits_below_clock_above_dock():
    layout = PRESETS["Projectivy Dock"]
    title = _layer(layout, "title")
    assert title.y >= 120
    assert title.y < 400
    assert layout.background.fade_bottom >= 0.4
    overview = _layer(layout, "overview")
    assert overview.y + (overview.height or 0) <= 1080 - SAFE_BOTTOM


def test_status_focus_keeps_pills_above_title():
    layout = PRESETS["Status Focus"]
    watch = _layer(layout, "watch_status")
    title = _layer(layout, "title")
    source = _layer(layout, "source")
    assert watch.y < title.y
    assert source.y > title.y
    assert watch.y >= 96


def test_title_box_caps_logo_and_overview_height_is_respected():
    for name, layout in PRESETS.items():
        title = _layer(layout, "title")
        max_w, max_h = logo_max_box(layout, title)
        assert max_w <= int(title.width), name
        assert max_h <= int(title.height), name
    prime_overview = _layer(PRESETS["Prime Cinematic"], "overview")
    assert overview_max_lines(prime_overview) <= 2
    netflix_overview = _layer(PRESETS["Netflix Hero"], "overview")
    assert overview_max_lines(netflix_overview) == 4


def test_presets_render_full_hd_chrome_and_stills():
    for name, layout in PRESETS.items():
        still = render_still(PROBE, layout)
        chrome = render_chrome(PROBE, layout)
        assert still.size == (1920, 1080), name
        assert chrome.size == (1920, 1080), name
        assert chrome.mode == "RGBA", name


def test_seed_presets_refreshes_stale_dna_and_keeps_user_copies(suite_dirs):
    layouts_mod = suite_dirs["layouts_mod"]
    layouts_dir = suite_dirs["layouts"]
    stale_path = layouts_dir / "Jellyfin Dense.json"
    stale = json.loads(stale_path.read_text(encoding="utf-8"))
    stale["dna_revision"] = 0
    stale["layers"] = []
    stale["title_display"] = "text"
    stale_path.write_text(json.dumps(stale), encoding="utf-8")
    custom_path = layouts_dir / "My Hero.json"
    custom_path.write_text(
        json.dumps(
            {
                "name": "My Hero",
                "preset": False,
                "preset_id": "netflix_hero",
                "dna_revision": 0,
                "layers": [{"id": "keep", "slot": "title"}],
            }
        ),
        encoding="utf-8",
    )
    layouts_mod.seed_presets()
    refreshed = json.loads(stale_path.read_text(encoding="utf-8"))
    assert refreshed["dna_revision"] == layouts_mod.DNA_REVISION
    assert any(layer["slot"] == "watch_status" for layer in refreshed["layers"])
    assert refreshed["title_display"] == "text"
    kept = json.loads(custom_path.read_text(encoding="utf-8"))
    assert kept["layers"] == [{"id": "keep", "slot": "title"}]


def test_seed_presets_skips_current_revision(suite_dirs):
    layouts_mod = suite_dirs["layouts_mod"]
    path = suite_dirs["layouts"] / "Netflix Hero.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    body["description"] = "user tweak at current revision"
    path.write_text(json.dumps(body), encoding="utf-8")
    layouts_mod.seed_presets()
    kept = json.loads(path.read_text(encoding="utf-8"))
    assert kept["description"] == "user tweak at current revision"
