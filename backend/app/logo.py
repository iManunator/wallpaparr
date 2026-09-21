"""Movie / series clearlogo helpers (Pillow, no numpy).

Behavior follows the WebGUI fork's *intent*: draw a logo when we have one,
otherwise the title; trim transparent padding; cap size so tall/square marks
do not dominate; lift dark logos on cinematic fades; keep a consistent gap
before metadata tags; stay inside Projectivy clock / dock safe zones.
"""

from __future__ import annotations

import io
from typing import Literal

from PIL import Image

from app.images import looks_like_image
from app.models import Layout, Layer

TitleDisplay = Literal["logo", "text", "auto"]

PADDING = 25
MAX_WIDTH = 1200
MAX_HEIGHT = 450
SAFE_LEFT = 72
SAFE_RIGHT = 72
SAFE_TOP = 96
SAFE_BOTTOM = 220
LUMINANCE_THRESHOLD = 100
MIN_MAX_WIDTH = 160
MIN_MAX_HEIGHT = 48


def normalize_title_display(value: str | None) -> TitleDisplay:
    raw = (value or "auto").strip().lower()
    if raw in ("logo", "text", "auto"):
        return raw  # type: ignore[return-value]
    return "auto"


def prefers_logo(mode: str | None) -> bool:
    return normalize_title_display(mode) != "text"


def title_layer(layout: Layout) -> Layer | None:
    for layer in layout.layers:
        if layer.slot == "title" and layer.visible:
            return layer
    return None


def load_logo(data: bytes | None) -> Image.Image | None:
    if not data or not looks_like_image(data):
        return None
    try:
        image = Image.open(io.BytesIO(data))
        return image.convert("RGBA")
    except Exception:
        return None


def trim_bbox(image: Image.Image) -> Image.Image:
    bbox = image.getbbox()
    if not bbox:
        return image
    return image.crop(bbox)


def smart_resize_logo(
    image: Image.Image,
    max_w: int = MAX_WIDTH,
    max_h: int = MAX_HEIGHT,
) -> Image.Image:
    """Crop empty alpha, then fit max_w×max_h. Tall/square marks get a shorter cap."""
    logo = trim_bbox(image.convert("RGBA"))
    src_w, src_h = logo.size
    if src_w <= 0 or src_h <= 0:
        return logo
    ratio = src_w / src_h
    effective_max_h = float(max_h)
    if ratio < 0.8:  # tall / vertical
        effective_max_h = max_h * 0.6
    elif ratio < 1.2:  # square / compact
        effective_max_h = max_h * 0.75
    scale = min(max_w / src_w, effective_max_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    if (new_w, new_h) == (src_w, src_h):
        return logo
    return logo.resize((new_w, new_h), Image.Resampling.LANCZOS)


def ensure_high_contrast(image: Image.Image, threshold: float = LUMINANCE_THRESHOLD) -> Image.Image:
    """If opaque pixels are darker than *threshold*, recolor to white and keep alpha."""
    img = image.convert("RGBA")
    sample = img.resize((48, 48), Image.Resampling.BOX) if max(img.size) > 48 else img
    lum_sum = 0.0
    count = 0
    px = sample.load()
    width, height = sample.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = px[x, y]
            if a > 0:
                lum_sum += 0.299 * r + 0.587 * g + 0.114 * b
                count += 1
    if count == 0 or (lum_sum / count) >= threshold:
        return img
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.paste((255, 255, 255, 255), mask=img.split()[3])
    return out


def logo_max_box(layout: Layout, layer: Layer | None = None) -> tuple[int, int]:
    layer = layer or title_layer(layout)
    canvas_w = layout.canvas_width
    canvas_h = layout.canvas_height
    inner_w = max(MIN_MAX_WIDTH, canvas_w - SAFE_LEFT - SAFE_RIGHT)
    inner_h = max(MIN_MAX_HEIGHT, canvas_h - SAFE_TOP - SAFE_BOTTOM)
    preferred_w = int(layer.width) if layer and layer.width else min(MAX_WIDTH, inner_w)
    preferred_h = int(layer.height) if layer and layer.height else min(MAX_HEIGHT, inner_h)
    max_w = max(MIN_MAX_WIDTH, min(MAX_WIDTH, preferred_w, inner_w))
    max_h = max(MIN_MAX_HEIGHT, min(MAX_HEIGHT, preferred_h, inner_h))
    return max_w, max_h


def prepare_logo(image: Image.Image, layout: Layout, layer: Layer | None = None) -> Image.Image:
    contrasted = ensure_high_contrast(image)
    max_w, max_h = logo_max_box(layout, layer)
    return smart_resize_logo(contrasted, max_w=max_w, max_h=max_h)


def clamp_logo_xy(
    x: int,
    y: int,
    width: int,
    height: int,
    canvas_w: int,
    canvas_h: int,
) -> tuple[int, int]:
    max_x = max(SAFE_LEFT, canvas_w - SAFE_RIGHT - width)
    max_y = max(SAFE_TOP, canvas_h - SAFE_BOTTOM - height)
    return (
        min(max(int(x), SAFE_LEFT), max_x),
        min(max(int(y), SAFE_TOP), max_y),
    )


def place_logo(layout: Layout, layer: Layer, size: tuple[int, int]) -> tuple[int, int]:
    return clamp_logo_xy(int(layer.x), int(layer.y), size[0], size[1], layout.canvas_width, layout.canvas_height)


def tag_shift(
    layout: Layout,
    title: Layer,
    logo_y: int,
    logo_h: int,
    padding: int = PADDING,
) -> int:
    """Push metadata down so the gap under the logo is at least *padding*."""
    logo_bottom = logo_y + logo_h
    meta = [int(layer.y) for layer in layout.layers if layer.visible and layer.slot != "title" and layer.y > title.y]
    if not meta:
        return 0
    first_meta = min(meta)
    desired = logo_bottom + max(0, padding)
    return max(0, int(desired - first_meta))


def layout_padding(layout: Layout) -> int:
    raw = getattr(layout, "logo_padding", PADDING)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = PADDING
    return max(8, min(80, value))
