"""Bundled cinematic layout presets and layout store."""

from __future__ import annotations

import json
from pathlib import Path

from app.catalog import safe_name
from app.config import LAYOUTS_DIR, ensure_dirs
from app.models import Layout, LayoutBackground, Layer

# Keys users can change on a bundled preset without losing them on a DNA refresh.
_OPTIONALITY = ("title_display", "show_watch_badge", "show_seerr_badge")

# Bump when bundled DNA changes so persisted preset JSON refreshes on boot.
# Custom layouts (preset=false) are never overwritten. Netflix Hero is the gold
# lock — do not drift its layer coordinates without an explicit DNA bump.
DNA_REVISION = 6


def _layers(*rows: dict) -> list[Layer]:
    return [Layer.model_validate(row) for row in rows]


def _layout_path(name: str) -> Path:
    """Resolve a layout name to a path inside LAYOUTS_DIR, rejecting traversal."""
    cleaned = safe_name(name)
    path = (LAYOUTS_DIR / f"{cleaned}.json").resolve()
    layouts_root = LAYOUTS_DIR.resolve()
    if layouts_root not in path.parents:
        raise ValueError("Invalid layout name")
    return path


PRESETS: dict[str, Layout] = {
    "Netflix Hero": Layout(
        name="Netflix Hero",
        preset=True,
        preset_id="netflix_hero",
        dna_revision=DNA_REVISION,
        description="Left-stacked hero chrome over a heavy left fade.",
        background=LayoutBackground(fade_left=0.48, fade_bottom=0.42, fade_top=0, fade_right=0),
        title_display="auto",
        layers=_layers(
            {"id": "title", "slot": "title", "x": 80, "y": 70, "width": 860, "height": 130, "font_size": 72, "font_weight": "bold"},
            {"id": "year", "slot": "year", "x": 80, "y": 220, "width": 110, "font_size": 26},
            {"id": "genres", "slot": "genres", "x": 200, "y": 220, "width": 340, "font_size": 26, "max_items": 3},
            {"id": "runtime", "slot": "runtime", "x": 560, "y": 220, "width": 150, "font_size": 26},
            {"id": "media_type", "slot": "media_type", "x": 726, "y": 220, "width": 150, "font_size": 26},
            {"id": "rating", "slot": "rating", "x": 80, "y": 268, "font_size": 32, "font_weight": "bold"},
            {"id": "watch", "slot": "watch_status", "x": 80, "y": 318, "font_size": 24},
            {"id": "overview", "slot": "overview", "x": 80, "y": 390, "width": 720, "height": 140, "font_size": 26},
        ),
    ),
    "Prime Cinematic": Layout(
        name="Prime Cinematic",
        preset=True,
        preset_id="prime_cinematic",
        dna_revision=DNA_REVISION,
        description="Low title card with a deep bottom gradient.",
        background=LayoutBackground(fade_left=0.18, fade_bottom=0.58, fade_top=0, fade_right=0, color="#0b1018"),
        title_display="auto",
        layers=_layers(
            {"id": "title", "slot": "title", "x": 96, "y": 488, "width": 1100, "height": 120, "font_size": 64, "font_weight": "bold"},
            {"id": "year", "slot": "year", "x": 96, "y": 628, "width": 108, "font_size": 24},
            {"id": "genres", "slot": "genres", "x": 220, "y": 628, "width": 464, "font_size": 24, "max_items": 3},
            {"id": "runtime", "slot": "runtime", "x": 700, "y": 628, "width": 160, "font_size": 24},
            {"id": "media_type", "slot": "media_type", "x": 876, "y": 628, "width": 160, "font_size": 24},
            {"id": "rating", "slot": "rating", "x": 96, "y": 676, "font_size": 28, "font_weight": "bold"},
            {"id": "watch", "slot": "watch_status", "x": 96, "y": 728, "font_size": 22},
            {"id": "overview", "slot": "overview", "x": 96, "y": 788, "width": 980, "height": 56, "font_size": 22},
        ),
    ),
    "Google TV Clean": Layout(
        name="Google TV Clean",
        preset=True,
        preset_id="google_tv_clean",
        dna_revision=DNA_REVISION,
        description="Minimal top-right metadata, lots of artwork breathing room.",
        background=LayoutBackground(fade_right=0, fade_bottom=0.22, fade_top=0, fade_left=0.02, fade_softness=0.6),
        title_display="auto",
        layers=_layers(
            {"id": "title", "slot": "title", "x": 1044, "y": 96, "width": 720, "height": 110, "font_size": 56, "font_weight": "bold"},
            {"id": "year", "slot": "year", "x": 1044, "y": 230, "width": 114, "font_size": 22, "color": "#d0d0d0"},
            {"id": "genres", "slot": "genres", "x": 1174, "y": 230, "width": 334, "font_size": 22, "color": "#d0d0d0", "max_items": 2},
            {"id": "runtime", "slot": "runtime", "x": 1524, "y": 230, "width": 150, "font_size": 22, "color": "#d0d0d0"},
            {"id": "media_type", "slot": "media_type", "x": 1690, "y": 230, "width": 150, "font_size": 22, "color": "#d0d0d0"},
            {"id": "watch", "slot": "watch_status", "x": 1044, "y": 286, "font_size": 20},
            {"id": "overview", "slot": "overview", "x": 1044, "y": 350, "width": 640, "height": 120, "font_size": 22, "color": "#e8e8e8"},
        ),
    ),
    "Status Focus": Layout(
        name="Status Focus",
        preset=True,
        preset_id="status_focus",
        dna_revision=DNA_REVISION,
        description="Watch-state and library badges anchored bottom-right.",
        background=LayoutBackground(fade_right=0, fade_left=0.05, fade_bottom=0.42, fade_top=0, color="#120808"),
        title_display="auto",
        layers=_layers(
            {"id": "watch", "slot": "watch_status", "x": 940, "y": 486, "font_size": 26, "color": "#ffcc66", "font_weight": "bold"},
            {"id": "title", "slot": "title", "x": 940, "y": 570, "width": 900, "height": 130, "font_size": 64, "font_weight": "bold"},
            {"id": "year", "slot": "year", "x": 940, "y": 720, "width": 124, "font_size": 24},
            {"id": "age", "slot": "age", "x": 1080, "y": 720, "width": 164, "font_size": 24},
            {"id": "runtime", "slot": "runtime", "x": 1260, "y": 720, "width": 160, "font_size": 24},
            {"id": "media_type", "slot": "media_type", "x": 1436, "y": 720, "width": 150, "font_size": 24},
            {"id": "rating", "slot": "rating", "x": 940, "y": 768, "font_size": 32, "font_weight": "bold"},
            {"id": "source", "slot": "source", "x": 940, "y": 830, "font_size": 22},
        ),
    ),
    "Jellyfin Dense": Layout(
        name="Jellyfin Dense",
        preset=True,
        preset_id="jellyfin_dense",
        dna_revision=DNA_REVISION,
        description="Packed bottom-left chrome for library browsing wallpapers.",
        background=LayoutBackground(fade_left=0.52, fade_bottom=0.5, fade_top=0),
        title_display="auto",
        layers=_layers(
            {"id": "title", "slot": "title", "x": 80, "y": 376, "width": 820, "height": 110, "font_size": 56, "font_weight": "bold"},
            {"id": "year", "slot": "year", "x": 80, "y": 506, "width": 124, "font_size": 22},
            {"id": "age", "slot": "age", "x": 220, "y": 506, "width": 164, "font_size": 22},
            {"id": "runtime", "slot": "runtime", "x": 400, "y": 506, "width": 164, "font_size": 22},
            {"id": "source", "slot": "source", "x": 580, "y": 506, "width": 160, "font_size": 22},
            {"id": "media_type", "slot": "media_type", "x": 756, "y": 506, "width": 150, "font_size": 22},
            {"id": "genres", "slot": "genres", "x": 80, "y": 552, "width": 900, "font_size": 22, "max_items": 5},
            {"id": "rating", "slot": "rating", "x": 80, "y": 600, "font_size": 28, "font_weight": "bold"},
            {"id": "watch", "slot": "watch_status", "x": 80, "y": 654, "font_size": 22},
            {"id": "overview", "slot": "overview", "x": 80, "y": 716, "width": 760, "height": 140, "font_size": 22},
        ),
    ),
    "Projectivy Dock": Layout(
        name="Projectivy Dock",
        preset=True,
        preset_id="projectivy_dock",
        dna_revision=DNA_REVISION,
        description="Safe-zone chrome: below the clock, above the Projectivy row dock.",
        background=LayoutBackground(fade_left=0.4, fade_bottom=0.48, fade_top=0, fade_right=0, fade_softness=0.5),
        title_display="auto",
        layers=_layers(
            {"id": "title", "slot": "title", "x": 88, "y": 140, "width": 900, "height": 120, "font_size": 64, "font_weight": "bold"},
            {"id": "year", "slot": "year", "x": 88, "y": 280, "width": 116, "font_size": 24},
            {"id": "genres", "slot": "genres", "x": 220, "y": 280, "width": 384, "font_size": 24, "max_items": 2},
            {"id": "runtime", "slot": "runtime", "x": 620, "y": 280, "width": 160, "font_size": 24},
            {"id": "media_type", "slot": "media_type", "x": 796, "y": 280, "width": 160, "font_size": 24},
            {"id": "rating", "slot": "rating", "x": 88, "y": 328, "font_size": 30, "font_weight": "bold"},
            {"id": "watch", "slot": "watch_status", "x": 88, "y": 384, "font_size": 22},
            {"id": "overview", "slot": "overview", "x": 88, "y": 448, "width": 760, "height": 120, "font_size": 24},
        ),
    ),
}


def seed_presets(force: bool = False) -> None:
    ensure_dirs()
    for layout in PRESETS.values():
        path = LAYOUTS_DIR / f"{layout.name}.json"
        existing: dict = {}
        if path.exists() and not force:
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
            # User copies (duplicate in the editor) keep preset=false.
            if existing.get("preset") is False:
                continue
            if (
                existing.get("preset_id") == layout.preset_id
                and int(existing.get("dna_revision") or 0) >= DNA_REVISION
            ):
                continue
        to_write = layout
        if existing.get("preset_id") == layout.preset_id:
            payload = layout.model_dump()
            for key in _OPTIONALITY:
                if key in existing:
                    payload[key] = existing[key]
            try:
                to_write = Layout.model_validate(payload)
            except Exception:
                to_write = layout
        path.write_text(to_write.model_dump_json(indent=2), encoding="utf-8")


def list_layouts() -> list[str]:
    seed_presets()
    names = {p.stem for p in LAYOUTS_DIR.glob("*.json")}
    names.update(PRESETS.keys())
    return sorted(names, key=str.lower)


def load_layout(name: str) -> Layout | None:
    seed_presets()
    try:
        path = _layout_path(name)
    except ValueError:
        return PRESETS.get(name)
    if path.is_file():
        return Layout.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return PRESETS.get(name)


def save_layout(layout: Layout) -> Layout:
    ensure_dirs()
    path = _layout_path(layout.name)
    path.write_text(layout.model_dump_json(indent=2), encoding="utf-8")
    return layout


def reset_layout(name: str) -> Layout | None:
    """Overwrite a bundled preset's saved JSON with its pristine DNA.

    Only meaningful for the six bundled presets — a custom layout (preset:
    false, e.g. an Editor "Duplicate") has no built-in default to revert to.
    """
    preset = PRESETS.get(name)
    if preset is None:
        return None
    return save_layout(preset)


def delete_layout(name: str) -> bool:
    if name in PRESETS:
        return False
    path = _layout_path(name)
    if path.is_file():
        path.unlink()
        return True
    return False
