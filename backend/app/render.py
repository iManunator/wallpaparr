"""Cinematic still renderer (Pillow)."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from app.chrome import (
    SEERR_SLOTS,
    WATCH_SLOTS,
    chrome_pill_metrics,
    draw_chrome_pill,
    pill_gap,
)
from app.logo import (
    layout_padding,
    load_logo,
    place_logo,
    prefers_logo,
    prepare_logo,
    tag_shift,
    title_layer,
)
from app.models import GradientStop, Layout, LayoutBackground, MediaItem
from app.seerr_status import seerr_badge, seerr_label
from app.watch import watch_badge, watch_label

CANVAS = (1920, 1080)

# Slots with their own dedicated wrap/fit logic or draw path — never row-compacted.
NO_FLOW_SLOTS = {"title", "overview"} | set(WATCH_SLOTS) | set(SEERR_SLOTS)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _hex_color(value: str) -> tuple[int, int, int, int]:
    raw = (value or "#ffffff").lstrip("#")
    if len(raw) == 6:
        r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
        return r, g, b, 255
    if len(raw) == 8:
        r, g, b, a = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), int(raw[6:8], 16)
        return r, g, b, a
    return 255, 255, 255, 255


def palette_for(title: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    digest = hashlib.sha256(title.encode("utf-8")).digest()
    a = (digest[0], digest[1], 40 + digest[2] % 80)
    b = (digest[3] % 60, digest[4] % 40, 20 + digest[5] % 50)
    return a, b


def synthetic_backdrop(title: str, size: tuple[int, int] = CANVAS) -> Image.Image:
    left, right = palette_for(title)
    image = Image.new("RGB", size, left)
    draw = ImageDraw.Draw(image)
    width, height = size
    for x in range(width):
        t = x / max(width - 1, 1)
        color = (
            int(left[0] * (1 - t) + right[0] * t),
            int(left[1] * (1 - t) + right[1] * t),
            int(left[2] * (1 - t) + right[2] * t),
        )
        draw.line([(x, 0), (x, height)], fill=color)
    overlay = Image.new("RGB", size, (8, 8, 12))
    image = Image.blend(image, overlay, 0.25)
    return image.filter(ImageFilter.GaussianBlur(radius=8))


def _load_image(path_or_bytes: str | Path | bytes | None, size: tuple[int, int]) -> Image.Image | None:
    if path_or_bytes is None:
        return None
    try:
        if isinstance(path_or_bytes, bytes):
            img = Image.open(io.BytesIO(path_or_bytes))
        else:
            p = Path(path_or_bytes)
            if not p.is_file():
                return None
            img = Image.open(p)
        img = img.convert("RGB")
        img.thumbnail((size[0] * 2, size[1] * 2), Image.Resampling.LANCZOS)
        # cover crop
        src_w, src_h = img.size
        target_w, target_h = size
        scale = max(target_w / src_w, target_h / src_h)
        resized = img.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
        left = (resized.width - target_w) // 2
        top = (resized.height - target_h) // 2
        return resized.crop((left, top, left + target_w, top + target_h))
    except Exception:
        return None


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _normalized_stops(bg: LayoutBackground) -> list[tuple[float, tuple[int, int, int, int]]]:
    master = _clamp(bg.gradient_opacity)
    raw = list(bg.gradient_stops or [])
    if not raw:
        raw = [
            GradientStop(color=bg.color, position=0.0, opacity=0.92),
            GradientStop(color=bg.color, position=1.0, opacity=0.0),
        ]
    stops: list[tuple[float, tuple[int, int, int, int]]] = []
    for stop in raw:
        r, g, b, a = _hex_color(stop.color)
        alpha = int(a * _clamp(stop.opacity) * master)
        stops.append((_clamp(stop.position), (r, g, b, alpha)))
    stops.sort(key=lambda item: item[0])
    if not any(item[0] <= 0.0 for item in stops):
        stops.insert(0, (0.0, stops[0][1]))
    if not any(item[0] >= 1.0 for item in stops):
        stops.append((1.0, stops[-1][1]))
    return stops


def _lerp_color(
    stops: list[tuple[float, tuple[int, int, int, int]]], t: float
) -> tuple[int, int, int, int]:
    t = _clamp(t)
    if t <= stops[0][0]:
        return stops[0][1]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            span = max(t1 - t0, 1e-6)
            u = _clamp((t - t0) / span)
            return tuple(int(a + (b - a) * u) for a, b in zip(c0, c1))  # type: ignore[return-value]
    return stops[-1][1]


def linear_gradient_rgba(size: tuple[int, int], bg: LayoutBackground) -> Image.Image:
    width, height = size
    stops = _normalized_stops(bg)
    diag = max(int((width**2 + height**2) ** 0.5) + 8, 8)
    strip = Image.new("RGBA", (diag, 1))
    px = strip.load()
    last = diag - 1 or 1
    for x in range(diag):
        px[x, 0] = _lerp_color(stops, x / last)
    band = strip.resize((diag, diag), Image.Resampling.BILINEAR)
    # CSS: 0deg = up, 90deg = right. A left-to-right strip is 90deg.
    rotated = band.rotate(90.0 - float(bg.gradient_angle or 90.0), resample=Image.Resampling.BICUBIC, expand=True)
    left = (rotated.width - width) // 2
    top = (rotated.height - height) // 2
    return rotated.crop((left, top, left + width, top + height))


def radial_gradient_rgba(size: tuple[int, int], bg: LayoutBackground) -> Image.Image:
    stops = _normalized_stops(bg)
    sample = 256
    shade = Image.radial_gradient("L").resize((sample, sample), Image.Resampling.BICUBIC)
    lut = [_lerp_color(stops, i / 255) for i in range(256)]
    out = Image.new("RGBA", (sample, sample))
    sp = shade.load()
    op = out.load()
    for y in range(sample):
        for x in range(sample):
            op[x, y] = lut[sp[x, y]]
    return out.resize(size, Image.Resampling.BICUBIC)


def gradient_overlay(size: tuple[int, int], bg: LayoutBackground) -> Image.Image | None:
    if bg.gradient_opacity <= 0.001:
        return None
    kind = (bg.gradient_type or "linear").lower()
    if kind == "radial":
        return radial_gradient_rgba(size, bg)
    return linear_gradient_rgba(size, bg)


def vignette_overlay(size: tuple[int, int], amount: float) -> Image.Image | None:
    strength = _clamp(amount)
    if strength <= 0.001:
        return None
    shade = Image.radial_gradient("L").resize(size, Image.Resampling.BICUBIC)
    # Extreme corners reach amount * 255 so a strong vignette is opaque there
    # and does not Ken-Burns with the plate after overlay.
    alpha = shade.point(lambda v: int(min(255, v * strength)))
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    overlay.putalpha(alpha)
    return overlay


def color_overlay(size: tuple[int, int], color: str, opacity: float) -> Image.Image | None:
    amount = _clamp(opacity)
    if amount <= 0.001:
        return None
    r, g, b, _ = _hex_color(color)
    return Image.new("RGBA", size, (r, g, b, int(255 * amount)))


def fade_alpha_mask(layout: Layout, size: tuple[int, int]) -> Image.Image:
    width, height = size
    bg = layout.background
    shade = Image.new("L", (width, height), 0)
    px = shade.load()
    left = max(bg.fade_left, 0.0)
    right = max(bg.fade_right, 0.0)
    top = max(bg.fade_top, 0.0)
    bottom = max(bg.fade_bottom, 0.0)
    soft = max(bg.fade_softness, 0.05)
    for y in range(height):
        ny = y / max(height - 1, 1)
        for x in range(0, width, 4):
            nx = x / max(width - 1, 1)
            edge = 0.0
            if nx < left:
                edge = max(edge, (left - nx) / max(left, 0.001))
            if nx > 1 - right:
                edge = max(edge, (nx - (1 - right)) / max(right, 0.001))
            if ny < top:
                edge = max(edge, (top - ny) / max(top, 0.001))
            if ny > 1 - bottom:
                edge = max(edge, (ny - (1 - bottom)) / max(bottom, 0.001))
            alpha = min(1.0, edge ** (0.35 + soft))
            # Snap the darkest rim to fully opaque so baked VIDEO letterbox /
            # corner shadows cannot leak plate motion when the plate Ken-Burns.
            if alpha >= 0.97:
                value = 255
            else:
                value = int(round(alpha * 255))
            for dx in range(4):
                if x + dx < width:
                    px[x + dx, y] = value
    return shade


def apply_cinematic_fade(base: Image.Image, layout: Layout) -> Image.Image:
    if layout.background.brightness != 1.0:
        base = ImageEnhance.Brightness(base).enhance(
            max(0.2, min(1.6, layout.background.brightness))
        )
    shade = fade_alpha_mask(layout, base.size)
    color = Image.new("RGB", base.size, _hex_color(layout.background.color)[:3])
    return Image.composite(color, base, shade)


def slot_text(item: MediaItem, slot: str, max_items: int | None = None) -> str:
    if slot == "title":
        return item.title
    if slot == "year":
        return str(item.year or "")
    if slot == "genres":
        names = item.genres[: max_items or 3]
        return "  ·  ".join(names)
    if slot == "runtime":
        return item.runtime
    if slot in ("rating", "primary_score"):
        return f"★ {item.rating:.1f}" if item.rating else ""
    if slot == "imdb_rating":
        return f"IMDb {item.imdb_rating:.1f}" if item.imdb_rating else ""
    if slot == "rotten_tomatoes":
        return f"🍅 {item.rotten_tomatoes}%" if item.rotten_tomatoes is not None else ""
    if slot == "metacritic":
        return f"MC {item.metacritic}" if item.metacritic is not None else ""
    if slot == "awards":
        return item.awards or ""
    if slot == "overview":
        return item.overview
    if slot in WATCH_SLOTS:
        return watch_label(item.watch_state) or (item.watch_state or "").replace("_", " ").title()
    if slot in SEERR_SLOTS:
        return seerr_label(item.library_state, item.availability, item.source)
    if slot in ("source", "provider_source"):
        return (item.source or "").title()
    if slot == "age":
        return item.official_rating
    if slot == "media_type":
        return "Series" if (item.media_type or "movie").lower() == "tv" else "Movie"
    return ""


def _flow_row_positions(
    draw: ImageDraw.ImageDraw,
    item: MediaItem,
    layout: Layout,
    skip: set[str],
) -> dict[str, int]:
    """Compact same-row metadata chips (year/genres/runtime/media_type/...).

    Each chip's `x` in the layout is sized for a worst-case reserved slot.
    When the real rendered text is shorter, that leaves a dead gap before
    the next chip. Group chips that share a y and, left to right, pull
    each one in to right after the previous chip's actual rendered end —
    but never past its own configured x, so a long value that fills its
    slot renders exactly where it always did.
    """
    gap = 18
    rows: dict[int, list] = {}
    for layer in layout.layers:
        if not layer.visible or layer.slot in NO_FLOW_SLOTS or layer.slot in skip:
            continue
        if layer.slot in WATCH_SLOTS and not getattr(layout, "show_watch_badge", True):
            continue
        if layer.slot in SEERR_SLOTS and not getattr(layout, "show_seerr_badge", True):
            continue
        text = slot_text(item, layer.slot, layer.max_items)
        if not text:
            continue
        rows.setdefault(round(layer.y), []).append(layer)

    positions: dict[str, int] = {}
    for group in rows.values():
        group.sort(key=lambda l: l.x)
        cursor: float | None = None
        for layer in group:
            text = slot_text(item, layer.slot, layer.max_items)
            bold = layer.font_weight in ("bold", "black", "semibold")
            font = _font(layer.font_size, bold=bold)
            if layer.width:
                text = _truncate(draw, text, font, int(layer.width))
            width = draw.textbbox((0, 0), text, font=font)[2]
            x = float(layer.x) if cursor is None else min(float(layer.x), cursor)
            positions[layer.id] = int(x)
            cursor = x + width + gap
    return positions


def _draw_text_layers(
    canvas: Image.Image,
    item: MediaItem,
    layout: Layout,
    *,
    skip_slots: set[str] | None = None,
    shift_after_y: float | None = None,
    y_delta: int = 0,
) -> None:
    skip = skip_slots or set()
    draw = ImageDraw.Draw(canvas, "RGBA")
    flow_x = _flow_row_positions(draw, item, layout, skip)
    for layer in layout.layers:
        if not layer.visible:
            continue
        if layer.slot in ("backdrop", "poster"):
            continue
        if layer.slot in skip:
            continue
        if layer.slot in WATCH_SLOTS and not getattr(layout, "show_watch_badge", True):
            continue
        if layer.slot in SEERR_SLOTS and not getattr(layout, "show_seerr_badge", True):
            continue
        text = slot_text(item, layer.slot, layer.max_items)
        if not text:
            continue
        bold = layer.font_weight in ("bold", "black", "semibold")
        font = _font(layer.font_size, bold=bold)
        color = _hex_color(layer.color)
        x, y = int(layer.x), int(layer.y)
        if layer.id in flow_x:
            x = flow_x[layer.id]
        if y_delta and shift_after_y is not None and layer.y > shift_after_y:
            y += y_delta
        if layer.slot in WATCH_SLOTS:
            _draw_watch_pill(draw, item, x, y, font, color)
            continue
        if layer.slot in SEERR_SLOTS:
            _draw_seerr_pill(draw, item, x, y, font, color)
            continue
        max_width = int(layer.width or 0)
        if max_width and layer.slot == "overview":
            wrapped = _wrap(draw, text, font, max_width)
            line_h = max(int(layer.font_size * 1.25), 1)
            max_lines = 4
            if layer.height:
                max_lines = max(1, min(4, int(layer.height) // line_h))
            text = "\n".join(wrapped[:max_lines])
        elif max_width and layer.slot == "title":
            text, font = _fit_title(draw, text, layer.font_size, bold, max_width)
        elif max_width:
            text = _truncate(draw, text, font, max_width)
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 180))
        draw.text((x, y), text, font=font, fill=color)


def _draw_watch_pill(
    draw: ImageDraw.ImageDraw,
    item: MediaItem,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fallback_color: tuple[int, int, int, int],
) -> tuple[int, int, int, int] | None:
    badge = watch_badge(item.watch_state)
    if not badge:
        return None
    fill = _hex_color(badge["color"]) if badge.get("color") else fallback_color
    return draw_chrome_pill(draw, badge["label"], x, y, font, fill)


def _draw_seerr_pill(
    draw: ImageDraw.ImageDraw,
    item: MediaItem,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fallback_color: tuple[int, int, int, int],
) -> tuple[int, int, int, int] | None:
    badge = seerr_badge(item.library_state, item.availability, item.source)
    if not badge:
        return None
    fill = _hex_color(badge["color"]) if badge.get("color") else fallback_color
    return draw_chrome_pill(draw, badge["label"], x, y, font, fill)


def _draw_logo_layer(canvas: Image.Image, layout: Layout, logo_bytes: bytes | None) -> tuple[bool, int]:
    """Paste a prepared logo. Returns (drew_logo, metadata_y_shift)."""
    if not prefers_logo(layout.title_display):
        return False, 0
    image = load_logo(logo_bytes)
    if image is None:
        return False, 0
    layer = title_layer(layout)
    if layer is None:
        return False, 0
    try:
        prepared = prepare_logo(image, layout, layer)
        x, y = place_logo(layout, layer, prepared.size)
        canvas.paste(prepared, (x, y), prepared)
        return True, tag_shift(layout, layer, y, prepared.height, layout_padding(layout))
    except Exception:
        return False, 0


def render_plate(
    item: MediaItem,
    layout: Layout,
    backdrop_bytes: bytes | None = None,
) -> Image.Image:
    """Artwork-only layer (moves more in parallax VIDEO)."""
    size = (layout.canvas_width, layout.canvas_height)
    backdrop = _load_image(backdrop_bytes, size) or _load_image(item.backdrop_path, size)
    if backdrop is None:
        backdrop = synthetic_backdrop(item.title, size)
    if layout.background.brightness != 1.0:
        backdrop = ImageEnhance.Brightness(backdrop).enhance(
            max(0.2, min(1.6, layout.background.brightness))
        )
    return backdrop.convert("RGB")


def render_chrome(item: MediaItem, layout: Layout, logo_bytes: bytes | None = None) -> Image.Image:
    """Transparent vignette + metadata (moves less / stays put in parallax VIDEO)."""
    size = (layout.canvas_width, layout.canvas_height)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    bg = layout.background
    extra = gradient_overlay(size, bg)
    if extra is not None:
        overlay = Image.alpha_composite(overlay, extra)
    wash_overlay = color_overlay(size, bg.overlay_color, bg.overlay_opacity)
    if wash_overlay is not None:
        overlay = Image.alpha_composite(overlay, wash_overlay)
    vignette = vignette_overlay(size, bg.vignette)
    if vignette is not None:
        overlay = Image.alpha_composite(overlay, vignette)
    mask = fade_alpha_mask(layout, size)
    wash = Image.new("RGBA", size, (*_hex_color(bg.color)[:3], 255))
    overlay = Image.composite(wash, overlay, mask)
    title = title_layer(layout)
    used_logo, y_delta = _draw_logo_layer(overlay, layout, logo_bytes)
    skip = {"title"} if used_logo else set()
    _draw_text_layers(
        overlay,
        item,
        layout,
        skip_slots=skip,
        shift_after_y=title.y if used_logo and title else None,
        y_delta=y_delta,
    )
    _ensure_status_pills(
        overlay,
        item,
        layout,
        shift_after_y=title.y if used_logo and title else None,
        y_delta=y_delta,
    )
    return overlay


def _default_badge_origin(
    layout: Layout,
    *,
    shift_after_y: float | None = None,
    y_delta: int = 0,
) -> tuple[int, int]:
    title = title_layer(layout)
    x, y = 80, 318
    if title:
        x, y = int(title.x), int(title.y) + max(int(title.font_size or 64) + 36, 96)
    if y_delta and shift_after_y is not None and y > shift_after_y:
        y += y_delta
    return x, y


def _shifted_layer_origin(
    layer,
    *,
    shift_after_y: float | None = None,
    y_delta: int = 0,
) -> tuple[int, int]:
    x, y = int(layer.x), int(layer.y)
    if y_delta and shift_after_y is not None and layer.y > shift_after_y:
        y += y_delta
    return x, y


def _ensure_status_pills(
    canvas: Image.Image,
    item: MediaItem,
    layout: Layout,
    *,
    shift_after_y: float | None = None,
    y_delta: int = 0,
) -> None:
    """Paint watch + Seerr pills on locked chrome when status is known.

    Layout DNA may already have a watch_status / seerr_status layer. Missing
    pills still drop in next to each other at a TV-safe default so IMAGE/VIDEO
    chrome stays obvious without moving with the plate.
    """
    draw = ImageDraw.Draw(canvas, "RGBA")
    show_watch = getattr(layout, "show_watch_badge", True)
    show_seerr = getattr(layout, "show_seerr_badge", True)
    watch_meta = watch_badge(item.watch_state) if show_watch else None
    seerr_meta = seerr_badge(item.library_state, item.availability, item.source) if show_seerr else None
    watch_layer = next((layer for layer in layout.layers if layer.visible and layer.slot in WATCH_SLOTS), None)
    seerr_layer = next((layer for layer in layout.layers if layer.visible and layer.slot in SEERR_SLOTS), None)

    watch_box: tuple[int, int, int, int] | None = None
    if watch_meta and watch_layer:
        wx, wy = _shifted_layer_origin(watch_layer, shift_after_y=shift_after_y, y_delta=y_delta)
        font = _font(watch_layer.font_size, watch_layer.font_weight in ("bold", "black", "semibold"))
        metrics = chrome_pill_metrics(draw, watch_meta["label"], font)
        watch_box = (wx, wy, wx + int(metrics["width"]), wy + int(metrics["height"]))
    elif watch_meta:
        x, y = _default_badge_origin(layout, shift_after_y=shift_after_y, y_delta=y_delta)
        watch_box = _draw_watch_pill(draw, item, x, y, _font(22), (255, 255, 255, 255))

    if not seerr_meta or seerr_layer:
        return
    if watch_box:
        font = _font(watch_layer.font_size if watch_layer else 22)
        gap = pill_gap(int(getattr(font, "size", 22) or 22))
        sx, sy = watch_box[2] + gap, watch_box[1]
        _draw_seerr_pill(draw, item, sx, sy, font, (255, 255, 255, 255))
        return
    if watch_layer:
        x, y = _shifted_layer_origin(watch_layer, shift_after_y=shift_after_y, y_delta=y_delta)
        _draw_seerr_pill(draw, item, x, y, _font(watch_layer.font_size), (255, 255, 255, 255))
        return
    x, y = _default_badge_origin(layout, shift_after_y=shift_after_y, y_delta=y_delta)
    _draw_seerr_pill(draw, item, x, y, _font(22), (255, 255, 255, 255))


def render_still(
    item: MediaItem,
    layout: Layout,
    backdrop_bytes: bytes | None = None,
    logo_bytes: bytes | None = None,
) -> Image.Image:
    plate = render_plate(item, layout, backdrop_bytes=backdrop_bytes)
    chrome = render_chrome(item, layout, logo_bytes=logo_bytes)
    return Image.alpha_composite(plate.convert("RGBA"), chrome).convert("RGB")


def _fit_font(
    draw: ImageDraw.ImageDraw, text: str, size: int, bold: bool, max_width: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Shrink the title font until it fits max_width, down to a floor.

    Titles are never truncated with an ellipsis — long Seerr/TMDB titles are
    common and cutting them off hides real information. A slightly smaller
    font on those rows only.
    """
    floor = max(12, int(size * 0.5))
    font = _font(size, bold=bold)
    while size > floor:
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            break
        size -= 2
        font = _font(size, bold=bold)
    return font


def _fit_title(
    draw: ImageDraw.ImageDraw, text: str, size: int, bold: bool, max_width: int,
) -> tuple[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    """Shrink the title font to fit max_width (see _fit_font); truncate with
    an ellipsis only in the rare case where even the shrink floor overflows.
    """
    font = _fit_font(draw, text, size, bold, max_width)
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] > max_width:
        text = _truncate(draw, text, font, max_width)
    return text, font


def _truncate(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    """Single-line ellipsis truncation so long metadata (genres, runtime) never
    bleeds into a neighbouring chip on the same row."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text
    ellipsis = "…"
    while text and draw.textbbox((0, 0), text + ellipsis, font=font)[2] > max_width:
        text = text[:-1].rstrip()
    return f"{text}{ellipsis}" if text else ellipsis


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def save_jpeg(image: Image.Image, dest: Path, quality: int = 90) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "JPEG", quality=quality, optimize=True)
    return dest


def save_png(image: Image.Image, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "PNG")
    return dest
