"""Parallax / Ken Burns / drift VIDEO loops for Projectivy.

Projectivy wallpaper plugins return either:
  - IMAGE (JPEG URL) — static, or
  - VIDEO (H.264 MP4 URL) — looping live wallpaper.

This module bakes the VIDEO as **layers**:

* **Background** — artwork plate. Subtle pan / zoom / drift (intensity presets).
  Optional parallax light-leak is a padded wash on this layer only.
* **Foreground / target** — logo or title, watch badges, Seerr/requestable chips,
  metadata chrome, **and static atmosphere** (vignette, letterbox shadows, edge
  gradients). Overlay is pinned at layout DNA coordinates. Chrome never Ken-Burns
  with the plate.

Do not Ken-Burns a flat JPEG that already has text or vignette burned in — that
makes title and shadows swim. Animate the plate (and optional leak), then overlay
the static chrome PNG each frame.

Ken Burns is **subpixel** (Pillow EXTENT + bicubic), not ffmpeg ``zoompan``.
zoompan is nearest-neighbour and stair-steps slow pans into stutter. Frames are
piped to x264 as constant-frame-rate H.264 Main @ L4.0 with no B-frames and no
scenecut so TV loop playback does not hitch at GOP boundaries.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image

from app.fsutil import promote_temp

STYLES = ("parallax", "kenburns", "drift")
QUALITIES = ("light", "standard", "cinematic")
# Distinct enough that Subtle / Balanced / Cinematic / Bold change the baked loop at a glance.
INTENSITY_PRESETS = {"subtle": 0.16, "balanced": 0.355, "cinematic": 0.55, "bold": 0.96}
# Keep jitter inside the named family, not across it.
_PRESET_BAND = {
    "subtle": (0.10, 0.28),
    "balanced": (0.29, 0.42),
    "cinematic": (0.43, 0.72),
    "bold": (0.82, 1.00),
}
_INTENSITY_JITTER = 0.08  # ±8% relative
_ZOOM_SCALE_SPAN = 0.06  # 0.94–1.06
_PAN_SCALE_SPAN = 0.06
_PAN_Y_RATIO_MIN = 0.10
_PAN_Y_RATIO_MAX = 0.18
_DEFAULT_PAN_Y_RATIO = 0.14  # CSS --motion-y / --motion-x

_BITRATE = {"light": "2800k", "standard": "4000k", "cinematic": "5500k"}
# Quality/preset duration tables are historical. First-run and missing-field
# fallbacks match AppSettings (15s / 24 fps / balanced) so bake, example
# config, and Settings cannot diverge.
_DEFAULT_DURATION = {"light": 8.0, "standard": 12.0, "cinematic": 16.0}
_PRESET_DURATION = {"subtle": 16.0, "balanced": 14.0, "cinematic": 12.0, "bold": 10.0}
_X264_PRESET = {"light": "fast", "standard": "medium", "cinematic": "slow"}
_DEFAULT_FPS = 24
_DEFAULT_PRESET = "balanced"
_DEFAULT_LOOP_SECONDS = 15.0
# Working plate multiplier. Float EXTENT samples this bitmap; not zoompan 2× NN.
_SUPER_SAMPLE = 2
_LEAK_RGB = (255, 122, 58)
_LEAK_ALPHA = 41  # ffmpeg colorchannelmixer=aa=0.16
# Short fade to/from black at each clip's edges. Projectivy tears down and
# recreates its player on every wallpaper swap (docs/PROJECTIVY.md) with no
# crossfade in the AIDL contract; landing that hard cut on a near-black frame
# instead of mid-scene makes it read as an intentional transition. Both are
# user-editable (motion_edge_fade_seconds / motion_fly_in_seconds).
# ``_FADE_SECONDS`` is the encode-helper default when a caller does not pass
# a duration; ``profile_from_settings`` uses AppSettings (1.0s).
_FADE_SECONDS = 0.35
_DEFAULT_EDGE_FADE_SECONDS = 1.0
_FLY_IN_SECONDS = 1.0
# Extra zoom-in at frame 0, eased out to exactly 0 by the end of the fly-in
# window so it hands off to the normal Ken Burns curve with no jump.
_FLY_IN_ZOOM_BOOST = 0.35


def intensity_from_preset(name: str | None) -> float:
    return INTENSITY_PRESETS.get((name or _DEFAULT_PRESET).strip().lower(), INTENSITY_PRESETS[_DEFAULT_PRESET])


@dataclass(frozen=True)
class MotionProfile:
    style: str = "parallax"
    quality: str = "light"
    intensity: float = 0.55
    duration: float = 12.0
    fps: int = 30
    width: int = 1920
    height: int = 1080
    light_leak: bool = True
    edge_fade: bool = True
    edge_fade_seconds: float = 0.35
    fly_in: bool = False
    fly_in_seconds: float = 1.0
    pan_x_sign: int = 1
    pan_y_sign: int = 1
    pan_y_ratio: float = _DEFAULT_PAN_Y_RATIO
    phase: float = 0.0
    zoom_scale: float = 1.0
    pan_scale: float = 1.0

    @property
    def frames(self) -> int:
        return max(int(round(self.duration * self.fps)), 2)

    @property
    def bitrate(self) -> str:
        return _BITRATE.get(self.quality, "2800k")

    @property
    def zoom_from(self) -> float:
        """Always ≥ 1 — CSS ``--motion-zoom-from`` never zooms out past the cover crop."""
        return {"parallax": 1.04, "kenburns": 1.015, "drift": 1.015}.get(self.normalized_style(), 1.015)

    @property
    def zoom_to(self) -> float:
        """CSS ``--motion-zoom-to`` (web/src/lib/motion.ts)."""
        i = self.intensity
        style = self.normalized_style()
        if style == "kenburns":
            return round(1 + i * 0.22, 4)
        if style == "drift":
            return round(1 + i * 0.08, 4)
        return round(1 + i * 0.18, 4)

    @property
    def bg_zoom_amp(self) -> float:
        # Floor keeps Subtle parallax zooming *in* when CSS to < from.
        base = round(max(0.008, self.zoom_to - self.zoom_from), 4)
        return round(max(0.008, base * float(self.zoom_scale)), 4)

    @property
    def bg_pan(self) -> float:
        """CSS ``--motion-x`` as output pixels (drift 7.4%, else 4.8%)."""
        pct = 7.4 if self.normalized_style() == "drift" else 4.8
        return round(self.width * (pct / 100.0) * self.intensity * float(self.pan_scale), 2)

    @property
    def fg_pan(self) -> float:
        """Foreground chrome is pinned. Intensity never pans or zooms metadata."""
        return 0.0

    @property
    def super_sample(self) -> int:
        return _SUPER_SAMPLE

    @property
    def x264_preset(self) -> str:
        return _X264_PRESET.get(self.quality, "medium")

    def normalized_style(self) -> str:
        style = (self.style or "parallax").strip().lower()
        return style if style in STYLES else "parallax"


@dataclass(frozen=True)
class KenBurnsWindow:
    """Float source-pixel crop mapped onto the output frame (subpixel Ken Burns)."""

    x0: float
    y0: float
    x1: float
    y1: float
    zoom: float
    ease: float


def profile_from_settings(settings) -> MotionProfile:
    quality = str(getattr(settings, "motion_quality", None) or "light").strip().lower()
    if quality not in QUALITIES:
        quality = "light"
    preset = str(getattr(settings, "motion_preset", None) or _DEFAULT_PRESET).strip().lower()
    if preset not in INTENSITY_PRESETS:
        preset = _DEFAULT_PRESET
    intensity = intensity_from_preset(preset)
    raw_intensity = getattr(settings, "motion_intensity", None)
    if raw_intensity is not None:
        raw_f = min(1.0, max(0.0, float(raw_intensity)))
        # Honor a custom slider when it diverges from the named preset.
        cinematic = INTENSITY_PRESETS["cinematic"]
        if abs(raw_f - intensity) > 0.02 and preset == "cinematic" and abs(raw_f - cinematic) > 0.02:
            intensity = raw_f
        elif abs(raw_f - intensity) <= 0.02:
            intensity = raw_f
    intensity = min(1.0, max(0.0, intensity))
    duration = getattr(settings, "motion_duration", None)
    if duration:
        duration_f = float(duration)
    else:
        duration_f = _DEFAULT_LOOP_SECONDS
    duration_f = min(24.0, max(2.0, duration_f))
    fps = int(getattr(settings, "motion_fps", None) or _DEFAULT_FPS)
    fps = min(30, max(12, fps))
    style = str(getattr(settings, "motion_style", None) or "parallax")
    leak = bool(getattr(settings, "light_leak", True))
    edge_fade = bool(getattr(settings, "motion_edge_fade", True))
    edge_fade_seconds = float(getattr(settings, "motion_edge_fade_seconds", None) or _DEFAULT_EDGE_FADE_SECONDS)
    edge_fade_seconds = min(2.5, max(0.1, edge_fade_seconds))
    fly_in = bool(getattr(settings, "motion_fly_in", True))
    fly_in_seconds = float(getattr(settings, "motion_fly_in_seconds", None) or _FLY_IN_SECONDS)
    fly_in_seconds = min(4.0, max(0.2, fly_in_seconds))
    return MotionProfile(
        style=style,
        quality=quality,
        intensity=intensity,
        duration=duration_f,
        fps=fps,
        light_leak=leak,
        edge_fade=edge_fade,
        edge_fade_seconds=edge_fade_seconds,
        fly_in=fly_in,
        fly_in_seconds=fly_in_seconds,
    )


def motion_seed_key(*parts: object) -> str:
    """Stable seed from title / path / id. First non-empty part wins (lowercased)."""
    for part in parts:
        text = str(part or "").strip()
        if text:
            return text.lower()
    return "wallpaparr"


def wallpaper_motion_seed(
    *,
    jellyfin_id: str | None = None,
    tmdb_id: str | None = None,
    imdb_id: str | None = None,
    filename: str | None = None,
    path: str | None = None,
    title: str | None = None,
) -> str:
    """Same id chain for CSS preview and ffmpeg bake."""
    return motion_seed_key(jellyfin_id, tmdb_id, imdb_id, filename or path, title)


def fnv1a32(text: str) -> int:
    h = 0x811C9DC5
    for byte in (text or "").encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def _lcg32(seed: int):
    """Numerical Recipes LCG — matched in ``web/src/lib/motion.ts``."""
    state = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal state
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        return state / 4294967296.0

    return rand


def _lerp(lo: float, hi: float, t: float) -> float:
    return lo + (hi - lo) * t


def vary_motion_profile(
    profile: MotionProfile,
    *,
    enabled: bool,
    seed: str,
    preset: str | None = None,
) -> MotionProfile:
    """Mild seeded drift. Off returns the CSS-matched profile unchanged.

    Shared with ``varyMotionProfile`` in ``web/src/lib/motion.ts`` (same LCG draws).
    """
    if not enabled:
        return profile
    rng = _lcg32(fnv1a32(motion_seed_key(seed)))
    jitter = _lerp(-_INTENSITY_JITTER, _INTENSITY_JITTER, rng())
    intensity = min(1.0, max(0.0, float(profile.intensity) * (1.0 + jitter)))
    name = (preset or "").strip().lower()
    if name in _PRESET_BAND:
        lo, hi = _PRESET_BAND[name]
        intensity = min(hi, max(lo, intensity))
    pan_x_sign = -1 if rng() < 0.5 else 1
    pan_y_sign = -1 if rng() < 0.5 else 1
    pan_y_ratio = round(_lerp(_PAN_Y_RATIO_MIN, _PAN_Y_RATIO_MAX, rng()), 4)
    phase = round(rng(), 4)
    zoom_scale = round(_lerp(1.0 - _ZOOM_SCALE_SPAN, 1.0 + _ZOOM_SCALE_SPAN, rng()), 4)
    pan_scale = round(_lerp(1.0 - _PAN_SCALE_SPAN, 1.0 + _PAN_SCALE_SPAN, rng()), 4)
    return replace(
        profile,
        intensity=round(intensity, 4),
        pan_x_sign=pan_x_sign,
        pan_y_sign=pan_y_sign,
        pan_y_ratio=pan_y_ratio,
        phase=phase,
        zoom_scale=zoom_scale,
        pan_scale=pan_scale,
    )


def profile_for_wallpaper(
    settings,
    *,
    jellyfin_id: str | None = None,
    tmdb_id: str | None = None,
    imdb_id: str | None = None,
    filename: str | None = None,
    path: str | None = None,
    title: str | None = None,
    seed: str | None = None,
) -> MotionProfile:
    """Bake profile: ``profile_from_settings`` plus optional per-title variety."""
    profile = profile_from_settings(settings)
    enabled = bool(getattr(settings, "motion_vary", True))
    key = seed or wallpaper_motion_seed(
        jellyfin_id=jellyfin_id,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
        filename=filename,
        path=path,
        title=title,
    )
    preset = str(getattr(settings, "motion_preset", None) or "")
    return vary_motion_profile(profile, enabled=enabled, seed=key, preset=preset)


def motion_preview_vars(profile: MotionProfile) -> dict[str, str]:
    """CSS variables matching ``motionPreviewVars`` in ``web/src/lib/motion.ts``.

    Identity profiles (vary off) keep the historical zoom/pan strings. Varied
    profiles apply signs, pan/zoom scale, axis ratio, and start phase.
    """
    style = profile.normalized_style()
    i = float(profile.intensity)
    if style == "kenburns":
        zoom = 1 + i * 0.22
    elif style == "drift":
        zoom = 1 + i * 0.08
    else:
        zoom = 1 + i * 0.18
    zoom_from = 1.04 if style == "parallax" else 1.015
    identity = (
        int(profile.pan_x_sign) == 1
        and int(profile.pan_y_sign) == 1
        and abs(float(profile.pan_scale) - 1.0) < 1e-9
        and abs(float(profile.zoom_scale) - 1.0) < 1e-9
        and abs(float(profile.pan_y_ratio) - _DEFAULT_PAN_Y_RATIO) < 1e-9
        and abs(float(profile.phase)) < 1e-9
    )
    if identity:
        pan_x = (7.4 if style == "drift" else 4.8) * i
        pan_y = (2.6 if style == "drift" else 1.7) * i
        signed_x = -pan_x
        signed_y = pan_y * 0.4
        zoom_to = zoom
        delay = 0.0
    else:
        pan_x = (7.4 if style == "drift" else 4.8) * i * float(profile.pan_scale)
        signed_x = -pan_x * int(profile.pan_x_sign)
        signed_y = pan_x * float(profile.pan_y_ratio) * int(profile.pan_y_sign)
        zoom_to = profile.zoom_from + profile.bg_zoom_amp
        delay = -(float(profile.phase) * max(2.0, float(profile.duration)))
    duration = max(2.0, float(profile.duration))
    duration_s = str(int(duration)) if duration == int(duration) else str(duration)
    vars_: dict[str, str] = {
        "--motion-zoom-from": "1.04" if style == "parallax" else "1.015",
        "--motion-zoom-to": str(zoom_to) if identity else str(float(f"{zoom_to:.4f}")),
        "--motion-x": f"{signed_x:.2f}%",
        "--motion-y": f"{signed_y:.2f}%",
        "--motion-duration": f"{duration_s}s",
    }
    if not identity:
        vars_["--motion-delay"] = f"{delay:.3f}s"
    return vars_


def pingpong_ease_t(t: float) -> float:
    """0 at loop ends, 1 at midpoint — CSS ease-in-out 0% / 50% / 100%.

    ``sin(2πt)`` zooms *out* for half the clip. Squared half-angle sine does not.
    ``t`` is loop phase in ``[0, 1]`` (frame ``n / frames``).
    """
    return math.sin(math.pi * t) ** 2


def pingpong_ease(frames: int, clock: str = "n") -> str:
    """ffmpeg-style expression of :func:`pingpong_ease_t` (no commas)."""
    return f"sin(PI*{clock}/{frames})*sin(PI*{clock}/{frames})"


def fly_in_boost(n: int, profile: MotionProfile) -> float:
    """Extra zoom-in at the very start of the clip, eased to exactly 0 — both
    value and slope — by the end of the fly-in window, so it hands off to the
    normal Ken Burns curve with no jump: a fast swoop in that settles into the
    steady parallax instead of a visible cut between two different motions.
    """
    if not profile.fly_in:
        return 0.0
    fly_in_frames = max(1, int(round(profile.fly_in_seconds * profile.fps)))
    if n >= fly_in_frames:
        return 0.0
    p = n / fly_in_frames
    return _FLY_IN_ZOOM_BOOST * (1.0 - p) ** 2


def ken_burns_window(n: int, profile: MotionProfile, src_w: int, src_h: int) -> KenBurnsWindow:
    """Subpixel source window for frame ``n``. ``n == frames`` matches ``n == 0``."""
    frames = max(int(profile.frames), 2)
    ease = pingpong_ease_t((n / frames + float(profile.phase)) % 1.0)
    zoom = profile.zoom_from + profile.bg_zoom_amp * ease + fly_in_boost(n, profile)
    win_w = src_w / zoom
    win_h = src_h / zoom
    pan_x = profile.bg_pan * int(profile.pan_x_sign) * (src_w / max(profile.width, 1)) * ease
    pan_y = (
        profile.bg_pan
        * float(profile.pan_y_ratio)
        * int(profile.pan_y_sign)
        * (src_h / max(profile.height, 1))
        * ease
    )
    x0 = src_w / 2.0 + pan_x - win_w / 2.0
    y0 = src_h / 2.0 + pan_y - win_h / 2.0
    max_x = max(0.0, src_w - win_w)
    max_y = max(0.0, src_h - win_h)
    x0 = min(max(x0, 0.0), max_x)
    y0 = min(max(y0, 0.0), max_y)
    return KenBurnsWindow(x0, y0, x0 + win_w, y0 + win_h, zoom, ease)


def leak_geometry(profile: MotionProfile) -> tuple[str, str, int, int]:
    """Oversized light-leak canvas that still covers the frame while it drifts.

    A WxH wash overlaid at a moving x,y uncovers the opposite edge — that reads as
    a vignette / letterbox crawling with the Ken Burns. Pad like CSS ``inset: -18%``
    so the leak stays under chrome and never scrapes the frame.
    """
    w, h, frames = profile.width, profile.height, profile.frames
    pan_x = int(w * 0.12)
    pan_y = int(h * 0.04)
    mx = max(int(w * 0.18), pan_x + 8)
    my = max(int(h * 0.18), pan_y + 8)
    ease = pingpong_ease(frames, "n")
    x = f"{-mx}+{pan_x}*{ease}"
    y = f"{-my}+{pan_y}*{ease}"
    return x, y, w + 2 * mx, h + 2 * my


def leak_offset(n: int, profile: MotionProfile) -> tuple[float, float]:
    """Subpixel top-left of the padded leak on the output frame."""
    w, h, frames = profile.width, profile.height, profile.frames
    pan_x = w * 0.12
    pan_y = h * 0.04
    mx = max(w * 0.18, pan_x + 8)
    my = max(h * 0.18, pan_y + 8)
    ease = pingpong_ease_t((n / max(frames, 2) + float(profile.phase)) % 1.0)
    return (
        -mx + pan_x * ease * int(profile.pan_x_sign),
        -my + pan_y * ease * int(profile.pan_y_sign),
    )


def max_motion_frame(frames: int) -> int:
    """Frame index where ping-pong ease is at 1 (peak zoom / pan, CSS 50%)."""
    return max(1, int(frames) // 2)


def _rate_bits(rate: str) -> int:
    raw = str(rate).strip().lower()
    if raw.endswith("k"):
        return int(float(raw[:-1]) * 1000)
    if raw.endswith("m"):
        return int(float(raw[:-1]) * 1_000_000)
    return int(float(raw))


def encoder_args(profile: MotionProfile, *, frames: int | None = None) -> list[str]:
    """Projectivy-safe x264: Main L4.0 yuv420p +faststart, CFR, no B-frames.

    ``maxrate`` is 2× the target so VBV does not underflow on pans. ``scenecut=0``
    plus closed GOP keeps keyframes on a cadence instead of hitching mid-motion.
    """
    nframes = int(frames if frames is not None else profile.frames)
    avg = _rate_bits(profile.bitrate)
    gop = max(int(profile.fps) * 2, 24)
    params = (
        f"keyint={gop}:min-keyint={gop}:scenecut=0:bframes=0:"
        f"open-gop=0:ref=1:weightp=0"
    )
    return [
        "-fps_mode", "cfr",
        "-frames:v", str(nframes),
        "-c:v", "libx264",
        "-preset", profile.x264_preset,
        "-pix_fmt", "yuv420p",
        "-profile:v", "main",
        "-level", "4.0",
        "-bf", "0",
        "-g", str(gop),
        "-b:v", profile.bitrate,
        "-maxrate", f"{(avg * 2) // 1000}k",
        "-bufsize", f"{max(avg * 4, 8_000_000) // 1000}k",
        "-x264-params", params,
        "-movflags", "+faststart",
        "-an",
    ]


def cover_rgb(image: Image.Image, width: int, height: int) -> Image.Image:
    """object-fit: cover into ``width`` × ``height`` RGB."""
    src = image.convert("RGB")
    sw, sh = src.size
    if sw == width and sh == height:
        return src
    scale = max(width / max(sw, 1), height / max(sh, 1))
    resized = src.resize((max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def make_leak_layer(profile: MotionProfile) -> Image.Image:
    _, _, lw, lh = leak_geometry(profile)
    leak = Image.new("RGBA", (lw, lh), (*_LEAK_RGB, _LEAK_ALPHA))
    return leak


def render_motion_frame(
    plate: Image.Image,
    n: int,
    profile: MotionProfile,
    *,
    chrome: Image.Image | None = None,
    leak: Image.Image | None = None,
) -> Image.Image:
    """One composited RGB frame: Ken-Burns plate, optional leak, locked chrome."""
    w, h = profile.width, profile.height
    window = ken_burns_window(n, profile, plate.width, plate.height)
    frame = plate.transform(
        (w, h),
        Image.Transform.EXTENT,
        (window.x0, window.y0, window.x1, window.y1),
        Image.Resampling.BICUBIC,
    )
    if leak is not None:
        lx, ly = leak_offset(n, profile)
        placed = leak.transform(
            (w, h),
            Image.Transform.AFFINE,
            (1.0, 0.0, -lx, 0.0, 1.0, -ly),
            Image.Resampling.BILINEAR,
        )
        rgba = frame.convert("RGBA")
        rgba.alpha_composite(placed)
        frame = rgba
    else:
        frame = frame.convert("RGBA")
    if chrome is not None:
        overlay = chrome.convert("RGBA")
        if overlay.size != (w, h):
            overlay = overlay.resize((w, h), Image.Resampling.LANCZOS)
        frame.alpha_composite(overlay)
    return frame.convert("RGB")


def edge_fade_frames(nframes: int, fps: float, fade_seconds: float = _FADE_SECONDS) -> int:
    """Frame count for the to/from-black fade at one edge of the clip.

    Capped at a quarter of the clip so short durations still leave a visible
    unfaded middle.
    """
    return max(1, min(int(round(fade_seconds * fps)), int(nframes) // 4))


def apply_edge_fade(
    frame: Image.Image, n: int, nframes: int, fps: float, fade_seconds: float = _FADE_SECONDS,
) -> Image.Image:
    """Blend towards black over the first/last :func:`edge_fade_frames` frames."""
    fade_frames = edge_fade_frames(nframes, fps, fade_seconds)
    if n < fade_frames:
        alpha = n / fade_frames
    elif n >= nframes - fade_frames:
        alpha = (nframes - 1 - n) / fade_frames
    else:
        return frame
    alpha = max(0.0, min(1.0, alpha))
    if alpha >= 0.999:
        return frame
    black = Image.new("RGB", frame.size, (0, 0, 0))
    return Image.blend(black, frame, alpha)


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def ffprobe_bin() -> str | None:
    return shutil.which("ffprobe")


def mp4_path_for(jpg: Path) -> Path:
    return jpg.with_suffix(".mp4")


def has_motion(jpg: Path) -> bool:
    mp4 = mp4_path_for(jpg)
    try:
        return jpg.is_file() and mp4.is_file() and mp4.stat().st_size > 1000
    except OSError:
        return False


def generate_motion(
    jpg: Path,
    *,
    profile: MotionProfile | None = None,
    quality: str | None = None,
    force: bool = False,
    plate: Path | None = None,
    chrome: Path | None = None,
) -> tuple[bool, str]:
    if not jpg.is_file():
        return False, "jpeg missing"
    if not force and has_motion(jpg):
        return True, "already exists"
    ff = ffmpeg_bin()
    if not ff:
        return False, "ffmpeg not found"
    if profile is None:
        quality_n = (quality or "light").strip().lower()
        if quality_n not in QUALITIES:
            quality_n = "light"
        profile = MotionProfile(
            quality=quality_n,
            duration=_DEFAULT_LOOP_SECONDS,
            fps=_DEFAULT_FPS,
            style="kenburns" if not chrome else "parallax",
        )
    use_chrome = bool(chrome and Path(chrome).is_file())
    src = plate if plate and Path(plate).is_file() else jpg
    try:
        plate_img = Image.open(src).convert("RGB")
    except OSError as exc:
        return False, f"plate unreadable: {exc}"
    w, h = profile.width, profile.height
    ss = max(int(profile.super_sample), 1)
    working = cover_rgb(plate_img, w, h)
    if ss > 1:
        working = working.resize((w * ss, h * ss), Image.Resampling.LANCZOS)
    chrome_img: Image.Image | None = None
    if use_chrome:
        try:
            chrome_img = Image.open(chrome).convert("RGBA")
        except OSError as exc:
            return False, f"chrome unreadable: {exc}"
        if chrome_img.size != (w, h):
            chrome_img = chrome_img.resize((w, h), Image.Resampling.LANCZOS)
    use_leak = bool(use_chrome and profile.light_leak and profile.normalized_style() == "parallax")
    leak_img = make_leak_layer(profile) if use_leak else None
    nframes = profile.frames
    mp4 = mp4_path_for(jpg)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    cmd = [
        ff, "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{w}x{h}",
        "-r", str(profile.fps),
        "-i", "-",
        *encoder_args(profile, frames=nframes),
        str(tmp_path),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.stdin is not None
        try:
            for n in range(nframes):
                frame = render_motion_frame(
                    working, n, profile, chrome=chrome_img, leak=leak_img,
                )
                if profile.edge_fade:
                    frame = apply_edge_fade(frame, n, nframes, profile.fps, profile.edge_fade_seconds)
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
            stderr = proc.stderr.read() if proc.stderr else b""
            stdout = proc.stdout.read() if proc.stdout else b""
            rc = proc.wait(timeout=480)
        except BrokenPipeError:
            stderr = proc.stderr.read() if proc.stderr else b""
            stdout = proc.stdout.read() if proc.stdout else b""
            rc = proc.wait(timeout=60)
        if rc != 0 or not tmp_path.is_file() or tmp_path.stat().st_size < 1000:
            text = (stderr or stdout or b"ffmpeg failed").decode("utf-8", "replace").strip()
            tail = text.splitlines()[-8:]
            return False, " | ".join(tail) or "ffmpeg failed"
        promote_temp(tmp_path, mp4)
        return True, str(mp4)
    except subprocess.TimeoutExpired:
        return False, "ffmpeg timeout"
    finally:
        if tmp_path.exists() and tmp_path != mp4:
            tmp_path.unlink(missing_ok=True)


def choose_delivery(
    *,
    image_url: str | None,
    video_url: str | None,
    prefer_video: bool,
    fallback_still: bool = True,
    media_type: str | None = None,
) -> tuple[str | None, str]:
    """Pick IMAGE vs VIDEO for a client. Always keeps image_url available for fallback."""
    has_video = bool(video_url) and (
        (media_type or "").lower() == "video" or str(video_url).lower().endswith(".mp4")
    )
    if prefer_video and has_video:
        return video_url, "video"
    if image_url:
        return image_url, "image"
    if fallback_still is False and has_video:
        return video_url, "video"
    return None, "image"
