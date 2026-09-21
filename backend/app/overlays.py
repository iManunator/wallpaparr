"""Optional overlay widgets composited onto stills / chrome.

Overlays are **off by default**. The clock widget is fully rendered from local
time (works in demo/offline mode). Home Assistant, news, and generic JSON are
shipped as *hooks*: they draw a demo card unless a future fetch is wired, so
the Projectivy IMAGE/VIDEO contract never depends on live I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

WIDGET_KINDS = ("clock", "ha", "ha_entity", "news", "json")


@dataclass
class OverlaySpec:
    kind: str
    x: int = 72
    y: int = 36
    width: int = 280
    height: int = 72
    opacity: float = 0.88
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def spec_from_dict(raw: dict[str, Any]) -> OverlaySpec | None:
    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in WIDGET_KINDS:
        return None
    return OverlaySpec(
        kind=kind,
        x=int(raw.get("x") or 72),
        y=int(raw.get("y") or 36),
        width=int(raw.get("width") or 280),
        height=int(raw.get("height") or 72),
        opacity=min(1.0, max(0.0, float(raw.get("opacity") or 0.88))),
        enabled=bool(raw.get("enabled", True)),
        config=dict(raw.get("config") or {}),
    )


def specs_from_settings(settings: Any) -> list[OverlaySpec]:
    if not bool(getattr(settings, "overlays_enabled", False)):
        return []
    specs: list[OverlaySpec] = []
    if bool(getattr(settings, "overlay_clock", True)):
        specs.append(OverlaySpec(kind="clock", x=72, y=36, width=300, height=78, opacity=0.9))
    for raw in getattr(settings, "overlays", None) or []:
        if not isinstance(raw, dict):
            continue
        spec = spec_from_dict(raw)
        if spec and spec.enabled:
            specs.append(spec)
    return specs


def _card_bg(draw: ImageDraw.ImageDraw, spec: OverlaySpec, alpha: int) -> None:
    x1, y1 = spec.x, spec.y
    x2, y2 = spec.x + spec.width, spec.y + spec.height
    draw.rounded_rectangle([x1, y1, x2, y2], radius=14, fill=(12, 14, 20, alpha))
    draw.rounded_rectangle([x1, y1, x2, y2], radius=14, outline=(226, 182, 87, min(255, alpha + 40)), width=1)


def _draw_lines(draw: ImageDraw.ImageDraw, spec: OverlaySpec, lines: list[tuple[str, int, bool]]) -> None:
    y = spec.y + 10
    for text, size, bold in lines:
        font = _font(size, bold=bold)
        draw.text((spec.x + 16, y), text, font=font, fill=(244, 239, 230, 255))
        y += size + 6


def render_widget(layer: Image.Image, spec: OverlaySpec, now: datetime) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    alpha = int(180 * spec.opacity)
    _card_bg(draw, spec, alpha)
    kind = spec.kind
    if kind == "clock":
        label = spec.config.get("timezone") or "Tonight"
        _draw_lines(
            draw,
            spec,
            [
                (now.strftime("%H:%M"), 28, True),
                (f"{label} · {now.strftime('%a')} {now.strftime('%d').lstrip('0') or '0'} {now.strftime('%b')}", 14, False),
            ],
        )
        return
    if kind in ("ha", "ha_entity"):
        text = str(spec.config.get("label") or spec.config.get("text") or "HA · demo 72°")
        _draw_lines(draw, spec, [("Home Assistant", 12, False), (text, 20, True)])
        return
    if kind == "news":
        text = str(spec.config.get("headline") or spec.config.get("text") or "News · demo headline")
        _draw_lines(draw, spec, [("Headlines", 12, False), (text[:48], 16, True)])
        return
    text = str(spec.config.get("text") or "JSON · demo")
    _draw_lines(draw, spec, [("Widget", 12, False), (text[:48], 16, True)])


def render_overlay_layer(
    size: tuple[int, int],
    specs: list[OverlaySpec],
    now: datetime | None = None,
) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    stamp = now or datetime.now()
    for spec in specs:
        if spec.enabled:
            render_widget(layer, spec, stamp)
    return layer


def apply_overlays(image: Image.Image, settings: Any, now: datetime | None = None) -> Image.Image:
    specs = specs_from_settings(settings)
    if not specs:
        return image
    layer = render_overlay_layer(image.size, specs, now=now)
    mode = image.mode
    base = image.convert("RGBA")
    out = Image.alpha_composite(base, layer)
    if mode == "RGB":
        return out.convert("RGB")
    return out
