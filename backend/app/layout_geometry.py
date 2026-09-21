"""TV-safe layout DNA geometry — Netflix Hero is the gold reference.

Used by tests (and seed refresh) so every bundled preset:
- stays inside Projectivy clock / dock margins
- keeps logo/title/badges from overlapping
- leaves a watch row wide enough for the auto-placed Seerr pill
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from app.chrome import chrome_pill_metrics, pill_gap
from app.logo import SAFE_BOTTOM, SAFE_LEFT, SAFE_RIGHT
from app.models import Layout, Layer
from app.render import _font, _wrap

# Left-column chrome may sit a little above SAFE_TOP (Netflix title y=70);
# the clock is top-right. Dock / rows still use SAFE_BOTTOM.
TV_OVERSCAN_TOP = 64
MIN_GAP = 8

SAMPLE = {
    "title": "Northlight",
    "year": "2024",
    # Realistic TMDB/Jellyfin genre names, not the short "Sci-Fi" style —
    # this is the actual worst case that overlaps a fixed-x neighbour.
    "genres": "Science Fiction  ·  Action & Adventure  ·  Documentary  ·  Animation  ·  War & Politics",
    "runtime": "2h 11m",
    "rating": "★ 8.4",
    "overview": "A cartographer maps a city that rearranges itself after dusk.",
    "watch_status": "Unwatched",
    "seerr_status": "Seerr only",
    "source": "Jellyseerr",
    "age": "PG-13",
    "media_type": "Series",
}

# Netflix Hero — do not drift these without an explicit DNA bump.
NETFLIX_GOLD = {
    "title": {"x": 80, "y": 70, "width": 860, "height": 130, "font_size": 72},
    "year": {"x": 80, "y": 220, "width": 110, "font_size": 26},
    "genres": {"x": 200, "y": 220, "width": 340, "font_size": 26},
    "runtime": {"x": 560, "y": 220, "width": 150, "font_size": 26},
    "media_type": {"x": 726, "y": 220, "width": 150, "font_size": 26},
    "rating": {"x": 80, "y": 268, "font_size": 32},
    "watch_status": {"x": 80, "y": 318, "font_size": 24},
    "overview": {"x": 80, "y": 390, "width": 720, "height": 140, "font_size": 26},
}


@dataclass(frozen=True)
class Box:
    id: str
    slot: str
    x0: float
    y0: float
    x1: float
    y1: float

    def overlaps(self, other: Box, gap: float = 0) -> bool:
        return not (
            self.x1 + gap <= other.x0
            or other.x1 + gap <= self.x0
            or self.y1 + gap <= other.y0
            or other.y1 + gap <= self.y0
        )


def _sample_text(layer: Layer) -> str:
    if layer.slot == "genres":
        parts = SAMPLE["genres"].split("  ·  ")
        n = layer.max_items or 3
        return "  ·  ".join(parts[:n])
    return SAMPLE.get(layer.slot, layer.slot)


def _text_size(text: str, font_size: int, bold: bool) -> tuple[int, int]:
    font = _font(font_size, bold)
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def _pill_box(label: str, x: int, y: int, font_size: int, bold: bool) -> tuple[int, int, int, int]:
    font = _font(font_size, bold)
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    metrics = chrome_pill_metrics(draw, label, font)
    return x, y, x + int(metrics["width"]), y + int(metrics["height"])


def overview_max_lines(layer: Layer) -> int:
    if not layer.height:
        return 4
    line_h = max(int(layer.font_size * 1.25), 1)
    return max(1, min(4, int(layer.height) // line_h))


def chrome_boxes(layout: Layout) -> list[Box]:
    """Estimated baked-chrome boxes for a worst-case demo title + Seerr pill."""
    boxes: list[Box] = []
    watch_box: Box | None = None
    for layer in layout.layers:
        if not layer.visible or layer.slot in ("backdrop", "poster"):
            continue
        bold = layer.font_weight in ("bold", "black", "semibold")
        x, y = int(layer.x), int(layer.y)
        if layer.slot in ("watch_status", "watch_state"):
            x0, y0, x1, y1 = _pill_box(SAMPLE["watch_status"], x, y, layer.font_size, bold)
            watch_box = Box(layer.id, layer.slot, x0, y0, x1, y1)
            boxes.append(watch_box)
            continue
        if layer.slot in ("seerr_status", "seerr_state"):
            x0, y0, x1, y1 = _pill_box(SAMPLE["seerr_status"], x, y, layer.font_size, bold)
            boxes.append(Box(layer.id, layer.slot, x0, y0, x1, y1))
            continue
        text = _sample_text(layer)
        if layer.slot == "overview":
            font = _font(layer.font_size, bold)
            draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
            width = int(layer.width or 720)
            lines = _wrap(draw, text, font, width)[: overview_max_lines(layer)]
            line_h = max(int(layer.font_size * 1.25), 1)
            height = max(int(layer.height or 0), line_h * max(len(lines), 1))
            boxes.append(Box(layer.id, layer.slot, x, y, x + width, y + height))
            continue
        tw, th = _text_size(text, layer.font_size, bold)
        if layer.slot == "title":
            width = int(layer.width or max(tw, 200))
            height = int(layer.height or max(th, layer.font_size))
            boxes.append(Box(layer.id, layer.slot, x, y, x + width, y + height))
            continue
        if layer.width:
            # Render-time truncation (_truncate in render.py) never lets the
            # baked text exceed the layer's width — model that same cap here.
            tw = min(tw, int(layer.width))
        boxes.append(Box(layer.id, layer.slot, x, y, x + max(tw, 8), y + max(th, layer.font_size)))

    if watch_box and not any(b.slot in ("seerr_status", "seerr_state") for b in boxes):
        font_size = next(
            (int(layer.font_size) for layer in layout.layers if layer.slot in ("watch_status", "watch_state")),
            22,
        )
        gap = pill_gap(font_size)
        x0, y0, x1, y1 = _pill_box(
            SAMPLE["seerr_status"],
            int(watch_box.x1) + gap,
            int(watch_box.y0),
            font_size,
            False,
        )
        boxes.append(Box("seerr-auto", "seerr_status", x0, y0, x1, y1))
    return boxes


def collisions(boxes: list[Box], gap: float = MIN_GAP) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            if a.overlaps(b, gap=gap):
                hits.append((a.id, b.id))
    return hits


def safe_rect(layout: Layout) -> tuple[int, int, int, int]:
    """Inclusive TV-safe rectangle. Top uses overscan (Netflix y=70), not clock-right SAFE_TOP."""
    w, h = layout.canvas_width, layout.canvas_height
    return SAFE_LEFT, TV_OVERSCAN_TOP, w - SAFE_RIGHT, h - SAFE_BOTTOM


def box_outside_safe(box: Box, layout: Layout) -> bool:
    left, top, right, bottom = safe_rect(layout)
    return box.x0 < left or box.y0 < top or box.x1 > right or box.y1 > bottom
