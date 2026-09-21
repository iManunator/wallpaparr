"""Shared TV-safe chrome pill geometry for watch + Seerr badges.

Used by the Pillow still/VIDEO renderer so baked pills match the web preview:
equal padding, capsule radius, glyph box optically centered in the pill.
"""

from __future__ import annotations

from typing import Any

from PIL import ImageDraw, ImageFont

# Match web `.chrome-pill` (padding 0.32em 0.72em, capsule radius).
PILL_PAD_X_EM = 0.72
PILL_PAD_Y_EM = 0.32
PILL_MIN_PAD_X = 12
PILL_MIN_PAD_Y = 6
PILL_GAP_EM = 0.5
PILL_MIN_GAP = 10
PILL_OUTLINE = 2
PILL_FILL = (8, 10, 14, 200)

WATCH_SLOTS = ("watch_status", "watch_state")
SEERR_SLOTS = ("seerr_status", "seerr_state")


def pill_padding(font_size: int) -> tuple[int, int]:
    size = max(int(font_size), 1)
    pad_x = max(PILL_MIN_PAD_X, round(size * PILL_PAD_X_EM))
    pad_y = max(PILL_MIN_PAD_Y, round(size * PILL_PAD_Y_EM))
    return pad_x, pad_y


def pill_gap(font_size: int) -> int:
    return max(PILL_MIN_GAP, round(max(int(font_size), 1) * PILL_GAP_EM))


def chrome_pill_metrics(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> dict[str, Any]:
    """Return pill size and text origin so the glyph bbox is centered.

    ``text_dx`` / ``text_dy`` are offsets from the pill's top-left to the
    ``draw.text`` origin. After drawing, the glyph box sits ``pad_x`` from
    the left/right and ``pad_y`` from the top/bottom.
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    left, top, right, bottom = bbox
    tw = right - left
    th = bottom - top
    font_size = int(getattr(font, "size", None) or max(th, 16))
    pad_x, pad_y = pill_padding(font_size)
    width = tw + pad_x * 2
    height = th + pad_y * 2
    return {
        "pad_x": pad_x,
        "pad_y": pad_y,
        "width": width,
        "height": height,
        "radius": max(height // 2, 1),
        "text_dx": pad_x - left,
        "text_dy": pad_y - top,
        "tw": tw,
        "th": th,
        "bbox": bbox,
        "font_size": font_size,
        "gap": pill_gap(font_size),
    }


def draw_chrome_pill(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    *,
    background: tuple[int, int, int, int] = PILL_FILL,
) -> tuple[int, int, int, int]:
    """Paint a capsule pill. Returns ``(x0, y0, x1, y1)``."""
    metrics = chrome_pill_metrics(draw, text, font)
    box = (int(x), int(y), int(x + metrics["width"]), int(y + metrics["height"]))
    draw.rounded_rectangle(
        box,
        radius=int(metrics["radius"]),
        fill=background,
        outline=fill,
        width=PILL_OUTLINE,
    )
    draw.text((x + metrics["text_dx"], y + metrics["text_dy"]), text, font=font, fill=fill)
    return box
