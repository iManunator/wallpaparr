from __future__ import annotations

from datetime import datetime

from PIL import Image

from app.models import AppSettings
from app.overlays import (
    OverlaySpec,
    apply_overlays,
    render_overlay_layer,
    spec_from_dict,
    specs_from_settings,
)


def test_overlays_off_by_default():
    settings = AppSettings()
    assert specs_from_settings(settings) == []
    base = Image.new("RGB", (320, 180), (10, 20, 30))
    out = apply_overlays(base, settings)
    assert out.size == base.size
    assert out.getpixel((10, 10)) == base.getpixel((10, 10))


def test_clock_widget_draws_pixels():
    specs = [OverlaySpec(kind="clock", x=10, y=10, width=200, height=70)]
    layer = render_overlay_layer((320, 180), specs, now=datetime(2026, 9, 18, 20, 45))
    assert layer.mode == "RGBA"
    assert layer.getpixel((20, 20))[3] > 0
    assert layer.getpixel((300, 160))[3] == 0


def test_stub_widget_kinds_render():
    for kind, cfg in (
        ("ha", {"label": "HA · demo 72°"}),
        ("news", {"headline": "Festival lights return"}),
        ("json", {"text": "Queue 12"}),
    ):
        spec = spec_from_dict({"kind": kind, "x": 8, "y": 8, "width": 180, "height": 64, "config": cfg})
        assert spec is not None
        layer = render_overlay_layer((240, 120), [spec], now=datetime(2026, 9, 18, 12, 0))
        assert layer.getpixel((20, 20))[3] > 0


def test_unknown_kind_ignored():
    assert spec_from_dict({"kind": "weather_station"}) is None


def test_settings_clock_toggle():
    settings = AppSettings(overlays_enabled=True, overlay_clock=True)
    specs = specs_from_settings(settings)
    assert [s.kind for s in specs] == ["clock"]
    settings.overlay_clock = False
    settings.overlays = [{"kind": "news", "x": 20, "y": 20, "width": 160, "height": 60}]
    specs = specs_from_settings(settings)
    assert [s.kind for s in specs] == ["news"]


def test_apply_overlays_changes_still_when_enabled():
    settings = AppSettings(overlays_enabled=True, overlay_clock=True)
    base = Image.new("RGB", (320, 180), (10, 20, 30))
    out = apply_overlays(base, settings, now=datetime(2026, 9, 18, 20, 45))
    assert out.mode == "RGB"
    assert out.getpixel((90, 50)) != base.getpixel((90, 50))
