from __future__ import annotations

import io

from PIL import Image

from app.layouts import PRESETS
from app.logo import (
    PADDING,
    SAFE_BOTTOM,
    SAFE_LEFT,
    SAFE_TOP,
    clamp_logo_xy,
    ensure_high_contrast,
    load_logo,
    smart_resize_logo,
    tag_shift,
)
from app.models import Layout, LayoutBackground, Layer, MediaItem
from app.render import render_chrome, render_still


def _png(size=(400, 120), color=(255, 40, 40, 255), bg=(0, 0, 0, 0)) -> bytes:
    image = Image.new("RGBA", size, bg)
    image.paste(color, (10, 10, size[0] - 10, size[1] - 10))
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def _layout(**kwargs) -> Layout:
    layers = kwargs.pop(
        "layers",
        [
            Layer(id="title", slot="title", x=80, y=70, width=860, height=130, font_size=72, font_weight="bold"),
            Layer(id="year", slot="year", x=80, y=220, font_size=26),
            Layer(id="genres", slot="genres", x=200, y=220, font_size=26),
        ],
    )
    return Layout(
        name="Logo Probe",
        canvas_width=1920,
        canvas_height=1080,
        background=LayoutBackground(fade_left=0, fade_right=0, fade_top=0, fade_bottom=0, gradient_opacity=0, vignette=0),
        layers=layers,
        **kwargs,
    )


def test_smart_resize_caps_wide_and_tall_logos():
    wide = smart_resize_logo(Image.new("RGBA", (2400, 200), (255, 255, 255, 255)))
    assert wide.size[0] <= 1200
    assert wide.size[1] <= 450
    tall = smart_resize_logo(Image.new("RGBA", (200, 800), (255, 255, 255, 255)))
    assert tall.size[1] <= int(450 * 0.6) + 1
    square = smart_resize_logo(Image.new("RGBA", (900, 900), (255, 255, 255, 255)))
    assert square.size[1] <= int(450 * 0.75) + 1


def test_trim_bbox_and_padding_gap():
    padded = Image.new("RGBA", (800, 400), (0, 0, 0, 0))
    padded.paste((255, 255, 255, 255), (200, 150, 500, 230))
    resized = smart_resize_logo(padded, max_w=600, max_h=200)
    assert resized.size[0] < 800
    title = Layer(id="title", slot="title", x=80, y=70, width=860, height=130)
    shift = tag_shift(_layout(), title, logo_y=70, logo_h=180, padding=PADDING)
    assert shift >= PADDING
    # year starts at 220; logo bottom 250 + 25 = 275 → shift 55
    assert shift == 55


def test_safe_zone_never_clips_logo():
    x, y = clamp_logo_xy(-40, 0, 400, 120, 1920, 1080)
    assert x >= SAFE_LEFT
    assert y >= SAFE_TOP
    x2, y2 = clamp_logo_xy(1800, 1000, 400, 200, 1920, 1080)
    assert x2 + 400 <= 1920 - 72
    assert y2 + 200 <= 1080 - SAFE_BOTTOM


def test_dark_logo_recolored_white():
    dark = Image.new("RGBA", (80, 40), (20, 20, 20, 255))
    out = ensure_high_contrast(dark, threshold=100)
    pixel = out.getpixel((10, 10))
    assert pixel[0] == 255 and pixel[1] == 255 and pixel[2] == 255
    assert pixel[3] == 255
    bright = Image.new("RGBA", (80, 40), (240, 240, 240, 255))
    kept = ensure_high_contrast(bright, threshold=100)
    assert kept.getpixel((10, 10))[0] >= 230


def test_logo_preferred_over_title_text():
    layout = _layout(title_display="auto")
    item = MediaItem(title="UNIQUE_TITLE_GLYPH", year=2024, genres=["Drama"])
    text_only = render_chrome(item, layout)
    with_logo = render_chrome(item, layout, logo_bytes=_png((500, 140), (255, 220, 40, 255)))
    # Title slot is around (80, 70); a bright gold logo should dominate that region.
    logo_px = with_logo.getpixel((120, 100))
    text_px = text_only.getpixel((120, 100))
    assert logo_px[0] > 200
    assert logo_px[1] > 150
    assert logo_px[0] > logo_px[2]
    assert logo_px != text_px


def test_missing_logo_falls_back_to_title_text():
    layout = _layout(title_display="auto")
    item = MediaItem(title="UNIQUE_TITLE_GLYPH", year=2024)
    chrome = render_chrome(item, layout, logo_bytes=None)
    empty = render_chrome(MediaItem(title=""), layout)
    title_region = chrome.crop((70, 50, 900, 180))
    empty_region = empty.crop((70, 50, 900, 180))
    assert title_region.getbbox() is not None
    assert empty_region.getbbox() is None


def test_title_display_text_ignores_logo():
    layout = _layout(title_display="text")
    item = MediaItem(title="UNIQUE_TITLE_GLYPH")
    with_logo = render_chrome(item, layout, logo_bytes=_png((500, 140), (0, 255, 0, 255)))
    without = render_chrome(item, layout)
    assert with_logo.getpixel((120, 100)) == without.getpixel((120, 100))


def test_load_logo_rejects_non_images():
    assert load_logo(b"<!DOCTYPE html>") is None
    assert load_logo(b"") is None
    assert load_logo(_png()) is not None


def test_netflix_hero_preset_has_title_display_auto():
    layout = PRESETS["Netflix Hero"]
    assert layout.title_display == "auto"
    assert layout.logo_padding == 25


def test_every_bundled_preset_keeps_logo_text_auto():
    for name, layout in PRESETS.items():
        assert layout.title_display == "auto", name
        assert layout.logo_padding == PADDING, name


def test_render_still_with_logo_keeps_full_hd():
    item = MediaItem(title="Northlight", year=2024, genres=["Sci-Fi"])
    image = render_still(item, PRESETS["Netflix Hero"], logo_bytes=_png())
    assert image.size == (1920, 1080)
    assert image.mode == "RGB"
