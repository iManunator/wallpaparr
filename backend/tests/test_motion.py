from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from app.layouts import PRESETS
from app.motion import (
    MotionProfile,
    apply_edge_fade,
    choose_delivery,
    edge_fade_frames,
    encoder_args,
    ffmpeg_bin,
    ffprobe_bin,
    fly_in_boost,
    generate_motion,
    has_motion,
    intensity_from_preset,
    ken_burns_window,
    leak_geometry,
    leak_offset,
    max_motion_frame,
    motion_preview_vars,
    motion_seed_key,
    pingpong_ease,
    pingpong_ease_t,
    profile_for_wallpaper,
    profile_from_settings,
    render_motion_frame,
    vary_motion_profile,
    wallpaper_motion_seed,
)
from app.models import AppSettings, Layout, LayoutBackground, MediaItem
from app.render import render_chrome, render_plate, render_still, save_jpeg, save_png


def _grab_frame(mp4: Path, frame: int, dest: Path) -> Image.Image:
    result = subprocess.run(
        [
            ffmpeg_bin(),
            "-y",
            "-i",
            str(mp4),
            "-vf",
            f"select=eq(n\\,{frame})",
            "-vframes",
            "1",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr[-500:]
    return Image.open(dest).convert("RGB")


def _channel_delta(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    return max(abs(x - y) for x, y in zip(a, b))


def _probe_stream(mp4: Path) -> dict:
    result = subprocess.run(
        [
            ffprobe_bin() or "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=avg_frame_rate,r_frame_rate,nb_frames,has_b_frames,profile,level,pix_fmt,codec_name",
            "-of",
            "json",
            str(mp4),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr[-500:]
    return json.loads(result.stdout)["streams"][0]


def _probe_frame_pts(mp4: Path) -> list[float]:
    result = subprocess.run(
        [
            ffprobe_bin() or "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=pts_time,pkt_pts_time,pict_type,key_frame",
            "-of",
            "json",
            str(mp4),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr[-500:]
    pts = []
    for frame in json.loads(result.stdout).get("frames", []):
        raw = frame.get("pts_time") or frame.get("pkt_pts_time")
        if raw not in (None, "N/A"):
            pts.append(float(raw))
    return pts


def _stripe_plate(width: int, height: int) -> Image.Image:
    plate = Image.new("RGB", (width, height))
    px = plate.load()
    for y in range(height):
        for x in range(width):
            v = 220 if (x // 4) % 2 == 0 else 40
            h = 220 if (y // 4) % 2 == 0 else 40
            px[x, y] = (v, h, 80)
    return plate


def test_leak_geometry_pads_beyond_pan():
    profile = MotionProfile(style="parallax", duration=6, fps=24, width=1920, height=1080, light_leak=True)
    x, y, lw, lh = leak_geometry(profile)
    assert lw > profile.width
    assert lh > profile.height
    assert x.startswith("-")
    assert y.startswith("-")
    assert "," not in x and "," not in y


def test_max_motion_frame_is_peak_sine():
    assert max_motion_frame(12) == 6
    assert max_motion_frame(24) == 12


def test_choose_delivery_prefers_video_when_asked():
    uri, kind = choose_delivery(
        image_url="http://x/a.jpg",
        video_url="http://x/a.mp4",
        prefer_video=True,
        media_type="video",
    )
    assert kind == "video"
    assert uri.endswith(".mp4")


def test_choose_delivery_falls_back_to_still():
    uri, kind = choose_delivery(
        image_url="http://x/a.jpg",
        video_url=None,
        prefer_video=True,
        fallback_still=True,
    )
    assert kind == "image"
    assert uri.endswith(".jpg")


def test_choose_delivery_without_fallback_and_no_video():
    uri, kind = choose_delivery(
        image_url=None,
        video_url=None,
        prefer_video=True,
        fallback_still=True,
    )
    assert uri is None
    assert kind == "image"


def test_profile_scales_with_intensity():
    low = MotionProfile(style="parallax", intensity=0.1)
    high = MotionProfile(style="parallax", intensity=1.0)
    assert high.bg_zoom_amp > low.bg_zoom_amp
    assert high.bg_pan > low.bg_pan
    assert high.fg_pan == 0
    assert low.fg_pan == 0


def test_unknown_style_normalizes_to_parallax():
    assert MotionProfile(style="parallelx").normalized_style() == "parallax"


def test_choose_delivery_video_without_fallback():
    uri, kind = choose_delivery(
        image_url=None,
        video_url="http://x/a.mp4",
        prefer_video=False,
        fallback_still=False,
        media_type="video",
    )
    assert kind == "video"
    assert uri.endswith(".mp4")


def test_profile_from_settings_defaults():
    profile = profile_from_settings(AppSettings(motion_style="drift", motion_quality="cinematic"))
    assert profile.normalized_style() == "drift"
    assert profile.duration >= 12.0
    assert profile.quality == "cinematic"


def test_profile_from_settings_missing_fields_match_app_settings():
    class Bare:
        pass

    profile = profile_from_settings(Bare())
    defaults = profile_from_settings(AppSettings())
    assert profile.fps == defaults.fps == 24
    assert profile.duration == defaults.duration == 15.0
    assert profile.intensity == defaults.intensity
    assert profile.fly_in is True
    assert profile.edge_fade_seconds == 1.0
    assert intensity_from_preset(None) == intensity_from_preset("balanced")


def test_encoder_is_projectivy_cfr_without_bframes():
    profile = MotionProfile(style="parallax", quality="cinematic", duration=12, fps=30)
    args = encoder_args(profile)
    joined = " ".join(args)
    assert "-profile:v main" in joined
    assert "-level 4.0" in joined
    assert "-pix_fmt yuv420p" in joined
    assert "+faststart" in joined
    assert "-fps_mode cfr" in joined
    assert "-bf 0" in joined
    assert "bframes=0" in joined
    assert "scenecut=0" in joined
    assert "open-gop=0" in joined
    assert "zoompan" not in joined
    # VBV headroom: maxrate is 2× target so pans do not underflow.
    assert "-maxrate 11000k" in joined
    assert "-b:v 5500k" in joined
    assert "-frames:v 360" in joined


def test_ken_burns_window_is_subpixel_pingpong():
    """Bake must zoom *in* and rest at the loop join — not a bipolar sine zoom-out."""
    profile = MotionProfile(style="parallax", intensity=0.55, duration=12, fps=30, width=1920, height=1080)
    start = ken_burns_window(0, profile, 1920, 1080)
    peak = ken_burns_window(max_motion_frame(profile.frames), profile, 1920, 1080)
    last = ken_burns_window(profile.frames - 1, profile, 1920, 1080)
    wrap = ken_burns_window(profile.frames, profile, 1920, 1080)
    assert pingpong_ease_t(0.0) == 0.0
    assert pingpong_ease_t(0.5) == pytest.approx(1.0)
    assert pingpong_ease_t(1.0) == pytest.approx(0.0)
    assert "sin(2*PI" not in pingpong_ease(profile.frames, "on")
    assert start.zoom == pytest.approx(profile.zoom_from)
    assert peak.zoom == pytest.approx(profile.zoom_from + profile.bg_zoom_amp)
    assert peak.zoom > start.zoom
    assert wrap.zoom == pytest.approx(start.zoom)
    assert wrap.x0 == pytest.approx(start.x0)
    assert abs(last.x0 - start.x0) < 1.0
    xs = [ken_burns_window(n, profile, 1920, 1080).x0 for n in range(profile.frames)]
    adj = [abs(xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    span = abs(xs[max_motion_frame(profile.frames)] - xs[0])
    assert span > 8
    assert max(adj) < span * 0.12
    # True subpixel path — windows are not snapped to integer source pixels.
    assert any(abs(x - round(x)) > 0.02 for x in xs)


def test_locked_chrome_does_not_ken_burns():
    profile = MotionProfile(style="kenburns", intensity=0.96, duration=2, fps=12, width=64, height=36, light_leak=False)
    plate = Image.new("RGB", (64, 36), (200, 24, 24))
    chrome = Image.new("RGBA", (64, 36), (0, 0, 0, 0))
    from PIL import ImageDraw

    ImageDraw.Draw(chrome).rectangle([0, 0, 20, 12], fill=(250, 250, 250, 255))
    first = render_motion_frame(plate, 0, profile, chrome=chrome)
    moved = render_motion_frame(plate, max_motion_frame(profile.frames), profile, chrome=chrome)
    assert _channel_delta(first.getpixel((4, 4)), moved.getpixel((4, 4))) <= 6


def test_parallax_light_leak_sits_under_locked_chrome():
    profile = MotionProfile(style="parallax", intensity=0.96, duration=2, fps=12, width=80, height=45, light_leak=True)
    x, y, lw, lh = leak_geometry(profile)
    assert lw > profile.width
    assert lh > profile.height
    assert x.startswith("-")
    assert "," not in x and "," not in y
    lx0, ly0 = leak_offset(0, profile)
    lx1, _ = leak_offset(max_motion_frame(profile.frames), profile)
    assert lx0 < 0 and ly0 < 0
    assert lx1 > lx0
    plate = Image.new("RGB", (80, 45), (10, 10, 10))
    chrome = Image.new("RGBA", (80, 45), (0, 0, 0, 0))
    from PIL import ImageDraw
    from app.motion import make_leak_layer

    ImageDraw.Draw(chrome).rectangle([0, 0, 80, 10], fill=(8, 8, 8, 255))
    leak = make_leak_layer(profile)
    first = render_motion_frame(plate, 0, profile, chrome=chrome, leak=leak)
    moved = render_motion_frame(plate, max_motion_frame(profile.frames), profile, chrome=chrome, leak=leak)
    # Opaque letterbox chrome stays put while the leak drifts underneath.
    assert _channel_delta(first.getpixel((8, 4)), moved.getpixel((8, 4))) <= 4


def test_intensity_presets():
    assert intensity_from_preset("subtle") == 0.16
    assert intensity_from_preset("balanced") == 0.355
    assert intensity_from_preset("bold") == 0.96
    assert intensity_from_preset("nope") == 0.355
    profile = profile_from_settings(AppSettings(motion_preset="bold", motion_intensity=0.55))
    assert profile.intensity == 0.96
    assert profile.light_leak is True


def test_intensity_presets_change_output_clearly():
    subtle = MotionProfile(style="parallax", intensity=0.16)
    cinematic = MotionProfile(style="parallax", intensity=0.55)
    bold = MotionProfile(style="parallax", intensity=0.96)
    assert cinematic.bg_zoom_amp > subtle.bg_zoom_amp * 1.4
    assert bold.bg_zoom_amp > cinematic.bg_zoom_amp * 1.25
    assert bold.bg_pan > subtle.bg_pan * 2


def test_kenburns_without_chrome_is_plate_only():
    profile = MotionProfile(style="kenburns", intensity=0.8, duration=2, fps=12, width=48, height=27, light_leak=False)
    plate = Image.new("RGB", (48, 27))
    px = plate.load()
    for y in range(27):
        for x in range(48):
            px[x, y] = (int(255 * x / 47), int(255 * y / 26), 40)
    first = render_motion_frame(plate, 0, profile)
    moved = render_motion_frame(plate, max_motion_frame(profile.frames), profile)
    assert _channel_delta(first.getpixel((24, 13)), moved.getpixel((24, 13))) >= 4


def test_bake_amplitude_tracks_css_preview():
    """web/src/lib/motion.ts --motion-zoom-* / --motion-x (cinematic 0.55)."""
    p = MotionProfile(style="parallax", intensity=0.55, width=1920, height=1080)
    assert p.zoom_from == 1.04
    assert abs(p.zoom_from + p.bg_zoom_amp - (1 + 0.55 * 0.18)) < 0.002
    assert abs(p.bg_pan - 1920 * 0.048 * 0.55) < 0.05
    k = MotionProfile(style="kenburns", intensity=0.55, width=1920, height=1080)
    assert k.zoom_from == 1.015
    assert abs(k.zoom_from + k.bg_zoom_amp - (1 + 0.55 * 0.22)) < 0.002
    d = MotionProfile(style="drift", intensity=0.55, width=1920, height=1080)
    assert d.zoom_from == 1.015
    assert abs(d.bg_pan - 1920 * 0.074 * 0.55) < 0.05


def test_profile_defaults_are_tv_smooth():
    profile = profile_from_settings(AppSettings())
    assert profile.fps == 24
    assert profile.x264_preset == "fast"
    assert profile.bitrate == "2800k"
    cinematic = profile_from_settings(AppSettings(motion_quality="cinematic"))
    assert cinematic.fps == 24
    assert cinematic.x264_preset == "slow"
    assert cinematic.duration >= 12.0
    assert cinematic.bitrate == "5500k"
    assert MotionProfile(quality="standard").x264_preset == "medium"


def test_motion_preview_vars_match_css_when_vary_off():
    p = MotionProfile(style="parallax", intensity=0.55, duration=12, width=1920, height=1080)
    css = motion_preview_vars(p)
    assert css["--motion-zoom-from"] == "1.04"
    assert abs(float(css["--motion-zoom-to"]) - (1 + 0.55 * 0.18)) < 1e-6
    assert css["--motion-x"] == "-2.64%"
    assert css["--motion-duration"] == "12s"
    assert "--motion-delay" not in css
    k = MotionProfile(style="kenburns", intensity=0.55, duration=12)
    assert motion_preview_vars(k)["--motion-zoom-from"] == "1.015"


def test_vary_off_is_stable_identity():
    base = profile_from_settings(AppSettings(motion_vary=False, motion_preset="cinematic"))
    a = vary_motion_profile(base, enabled=False, seed="northlight")
    b = vary_motion_profile(base, enabled=False, seed="harbor")
    assert a == b == base
    assert a.phase == 0.0
    assert a.pan_x_sign == 1
    assert a.zoom_scale == 1.0
    assert motion_preview_vars(a)["--motion-x"] == "-2.64%"


def test_vary_on_is_seeded_within_preset_band():
    base = profile_from_settings(AppSettings(motion_vary=True, motion_preset="cinematic"))
    a = vary_motion_profile(base, enabled=True, seed="demo-jf-1", preset="cinematic")
    b = vary_motion_profile(base, enabled=True, seed="demo-jf-1", preset="cinematic")
    c = vary_motion_profile(base, enabled=True, seed="demo-jf-2", preset="cinematic")
    assert a == b
    assert a != c
    assert 0.40 <= a.intensity <= 0.72
    assert 0.40 <= c.intensity <= 0.72
    assert a.pan_x_sign in (-1, 1)
    assert a.pan_y_sign in (-1, 1)
    assert 0.10 <= a.pan_y_ratio <= 0.18
    assert 0.0 <= a.phase < 1.0
    assert 0.94 <= a.zoom_scale <= 1.06
    assert 0.94 <= a.pan_scale <= 1.06
    subtle = vary_motion_profile(
        MotionProfile(intensity=0.16), enabled=True, seed="demo-jf-1", preset="subtle"
    )
    bold = vary_motion_profile(
        MotionProfile(intensity=0.96), enabled=True, seed="demo-jf-1", preset="bold"
    )
    assert 0.10 <= subtle.intensity <= 0.28
    assert 0.82 <= bold.intensity <= 1.0


def test_preview_vars_and_bake_share_variation_helper():
    base = MotionProfile(style="parallax", intensity=0.55, duration=12, width=1920, height=1080)
    varied = vary_motion_profile(base, enabled=True, seed="demo-jf-1", preset="cinematic")
    css = motion_preview_vars(varied)
    start = ken_burns_window(0, varied, 1920, 1080)
    assert start.ease == pytest.approx(pingpong_ease_t(varied.phase % 1.0))
    peak_n = max(1, int(round(((0.5 - varied.phase) % 1.0) * varied.frames))) % varied.frames
    peak = ken_burns_window(peak_n, varied, 1920, 1080)
    assert peak.zoom == pytest.approx(varied.zoom_from + varied.bg_zoom_amp, rel=1e-3)
    assert float(css["--motion-zoom-to"]) == pytest.approx(varied.zoom_from + varied.bg_zoom_amp, abs=0.002)
    pan_pct = 4.8 * varied.intensity * varied.pan_scale
    signed_x = -pan_pct * varied.pan_x_sign
    assert css["--motion-x"] == f"{signed_x:.2f}%"
    assert css["--motion-delay"] == f"{(-(varied.phase * 12)):.3f}s"
    wrap = ken_burns_window(varied.frames, varied, 1920, 1080)
    assert wrap.zoom == pytest.approx(start.zoom)
    assert wrap.x0 == pytest.approx(start.x0)


def test_profile_for_wallpaper_respects_toggle_and_seed_chain():
    off = AppSettings(motion_vary=False, motion_preset="cinematic")
    on = AppSettings(motion_vary=True, motion_preset="cinematic")
    a = profile_for_wallpaper(on, jellyfin_id="demo-jf-1", title="Northlight")
    b = profile_for_wallpaper(on, jellyfin_id="demo-jf-1", filename="other.jpg", title="Renamed")
    c = profile_for_wallpaper(on, jellyfin_id="demo-jf-2", title="Harbor Season")
    d = profile_for_wallpaper(off, jellyfin_id="demo-jf-1", title="Northlight")
    e = profile_for_wallpaper(off, jellyfin_id="demo-jf-2", title="Harbor Season")
    assert a == b
    assert a != c
    assert d == e
    assert d.intensity == pytest.approx(0.55)
    assert wallpaper_motion_seed(jellyfin_id="demo-jf-1", title="Northlight") == motion_seed_key("demo-jf-1")


def test_python_matches_web_variation_golden():
    """Lock the LCG draws shared with web/src/lib/motion.ts (seed demo-jf-1)."""
    p = vary_motion_profile(
        MotionProfile(style="parallax", intensity=0.55, duration=12),
        enabled=True,
        seed="demo-jf-1",
        preset="cinematic",
    )
    assert p.intensity == 0.5582
    assert p.pan_x_sign == -1
    assert p.pan_y_sign == 1
    assert p.pan_y_ratio == 0.1025
    assert p.phase == 0.5727
    assert p.zoom_scale == 0.9996
    assert p.pan_scale == 1.0543
    css = motion_preview_vars(p)
    assert css["--motion-x"] == "2.82%"
    assert css["--motion-y"] == "0.29%"
    assert css["--motion-zoom-to"] == "1.1005"
    assert css["--motion-delay"] == "-6.872s"


def test_profile_defaults_include_motion_vary_on():
    settings = AppSettings()
    assert settings.motion_vary is True
    item = MediaItem(title="Depth", year=2024, overview="Parallax", rating=8.2, genres=["Sci-Fi"])
    chrome = render_chrome(item, PRESETS["Netflix Hero"])
    assert chrome.mode == "RGBA"
    assert chrome.size == (1920, 1080)
    # Some pixels remain fully transparent (artwork shows through).
    extrema = chrome.getextrema()
    assert extrema[3][0] == 0


def test_plate_has_no_alpha():
    item = MediaItem(title="Depth", year=2024)
    plate = render_plate(item, PRESETS["Netflix Hero"])
    assert plate.mode == "RGB"


@pytest.mark.skipif(ffmpeg_bin() is None, reason="ffmpeg not installed")
def test_ffmpeg_bakes_small_parallax_loop(tmp_path: Path):
    item = MediaItem(title="Loop", year=2021, overview="Motion", rating=7.5, genres=["Drama"])
    layout = PRESETS["Status Focus"]
    still = render_still(item, layout)
    jpg = tmp_path / "loop.jpg"
    plate = tmp_path / "loop_plate.jpg"
    chrome = tmp_path / "loop_chrome.png"
    save_jpeg(still, jpg)
    save_jpeg(render_plate(item, layout), plate)
    save_png(render_chrome(item, layout), chrome)
    # Tiny encode for CI speed: 320x180, 1s.
    profile = MotionProfile(
        style="parallax",
        quality="light",
        intensity=0.5,
        duration=1.0,
        fps=12,
        width=320,
        height=180,
        light_leak=False,
    )
    ok, msg = generate_motion(jpg, profile=profile, force=True, plate=plate, chrome=chrome)
    assert ok, msg
    assert has_motion(jpg)
    assert jpg.with_suffix(".mp4").stat().st_size > 1000
    leak_profile = MotionProfile(
        style="parallax",
        quality="light",
        intensity=0.5,
        duration=1.0,
        fps=12,
        width=320,
        height=180,
        light_leak=True,
    )
    ok, msg = generate_motion(jpg, profile=leak_profile, force=True, plate=plate, chrome=chrome)
    assert ok, msg


def test_edge_fade_frames_scales_with_fps_and_caps_at_quarter_clip():
    assert edge_fade_frames(120, 30) == 10
    assert edge_fade_frames(12, 12) == 3


def test_apply_edge_fade_darkens_only_the_edges():
    frame = Image.new("RGB", (4, 4), (200, 200, 200))
    nframes, fps = 12, 12
    assert apply_edge_fade(frame, 0, nframes, fps).getpixel((0, 0)) == (0, 0, 0)
    assert apply_edge_fade(frame, nframes - 1, nframes, fps).getpixel((0, 0)) == (0, 0, 0)
    assert apply_edge_fade(frame, nframes // 2, nframes, fps).getpixel((0, 0)) == (200, 200, 200)


def test_edge_fade_seconds_is_configurable():
    # Longer fade duration -> more frames faded, same cap logic applies.
    assert edge_fade_frames(120, 30, fade_seconds=1.0) == 30
    assert edge_fade_frames(120, 30, fade_seconds=0.1) == 3
    frame = Image.new("RGB", (4, 4), (200, 200, 200))
    # With a 1s fade at 30fps, frame 10 (0.33s in) is still fading.
    assert apply_edge_fade(frame, 10, 120, 30, fade_seconds=1.0) != frame
    # The same frame is past a short 0.1s (3-frame) fade window.
    assert apply_edge_fade(frame, 10, 120, 30, fade_seconds=0.1) == frame


def test_fly_in_boost_decays_to_exactly_zero_at_window_end():
    profile = MotionProfile(fly_in=True, fly_in_seconds=1.0, fps=30)
    assert fly_in_boost(0, profile) > 0
    assert fly_in_boost(0, profile) == pytest.approx(0.35)
    mid = fly_in_boost(15, profile)
    assert 0 < mid < fly_in_boost(0, profile)
    assert fly_in_boost(30, profile) == 0.0
    assert fly_in_boost(60, profile) == 0.0


def test_fly_in_boost_can_be_disabled():
    profile = MotionProfile(fly_in=False)
    assert profile.fly_in is False
    assert fly_in_boost(0, profile) == 0.0


def test_motion_profile_dataclass_defaults_match_app_settings():
    profile = MotionProfile()
    defaults = profile_from_settings(AppSettings())
    assert profile.fps == defaults.fps == 24
    assert profile.duration == defaults.duration == 15.0
    assert profile.fly_in is True
    assert profile.edge_fade is True
    assert profile.edge_fade_seconds == 1.0
    assert profile.intensity == intensity_from_preset("balanced")


def test_fly_in_zooms_in_further_at_start_than_normal_curve():
    base = MotionProfile(style="kenburns", intensity=0.55, duration=4.0, fps=30)
    boosted = MotionProfile(
        style="kenburns", intensity=0.55, duration=4.0, fps=30, fly_in=True, fly_in_seconds=1.0,
    )
    plain_zoom = ken_burns_window(0, base, 1000, 1000).zoom
    fly_in_zoom = ken_burns_window(0, boosted, 1000, 1000).zoom
    assert fly_in_zoom > plain_zoom
    # By the end of the fly-in window the two curves match exactly.
    end_frame = int(1.0 * 30)
    assert ken_burns_window(end_frame, base, 1000, 1000).zoom == pytest.approx(
        ken_burns_window(end_frame, boosted, 1000, 1000).zoom
    )


@pytest.mark.skipif(ffmpeg_bin() is None, reason="ffmpeg not installed")
def test_ffmpeg_keeps_chrome_pinned_on_kenburns(tmp_path: Path):
    from PIL import ImageDraw

    width, height = 320, 180
    plate_img = Image.new("RGB", (width, height), (200, 24, 24))
    chrome_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(chrome_img).rectangle([0, 0, 56, 32], fill=(250, 250, 250, 255))
    jpg = tmp_path / "locked.jpg"
    plate = tmp_path / "locked_plate.jpg"
    chrome = tmp_path / "locked_chrome.png"
    save_jpeg(plate_img, jpg)
    save_jpeg(plate_img, plate)
    save_png(chrome_img, chrome)
    profile = MotionProfile(
        style="kenburns",
        quality="light",
        intensity=0.96,
        duration=1.0,
        fps=12,
        width=width,
        height=height,
        light_leak=False,
    )
    ok, msg = generate_motion(jpg, profile=profile, force=True, plate=plate, chrome=chrome)
    assert ok, msg
    mp4 = jpg.with_suffix(".mp4")
    peak = max_motion_frame(profile.frames)
    fade_frames = edge_fade_frames(profile.frames, profile.fps)
    first = _grab_frame(mp4, fade_frames, tmp_path / "f0.png")
    moved = _grab_frame(mp4, peak, tmp_path / "fpeak.png")
    p0 = first.getpixel((10, 8))
    p1 = moved.getpixel((10, 8))
    assert min(p0) > 180, p0
    assert min(p1) > 180, p1
    assert _channel_delta(p0, p1) <= 6, (p0, p1)


@pytest.mark.skipif(ffmpeg_bin() is None, reason="ffmpeg not installed")
def test_ffmpeg_keeps_vignette_and_letterbox_locked_while_plate_moves(tmp_path: Path):
    """Atmosphere stays pinned; only the art plate Ken-Burns.

    Default parallax bakes a light-leak under chrome. A same-size leak that pans
    uncovers the frame edge and looks like a moving vignette — that must not happen.
    """
    from PIL import ImageDraw

    width, height = 320, 180
    plate_img = Image.new("RGB", (width, height))
    px = plate_img.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = (int(255 * x / (width - 1)), int(255 * y / (height - 1)), 40)

    item = MediaItem(title="Probe")
    layout = Layout(
        name="Locked atmosphere",
        canvas_width=width,
        canvas_height=height,
        background=LayoutBackground(
            fade_left=0.0,
            fade_right=0.0,
            fade_top=0.22,
            fade_bottom=0.22,
            fade_softness=0.2,
            vignette=0.9,
            overlay_opacity=0,
            gradient_opacity=0,
        ),
        layers=[],
    )
    chrome_img = render_chrome(item, layout)
    # Guarantee an opaque letterbox sample even if the fade falloff is soft.
    ImageDraw.Draw(chrome_img).rectangle([0, 0, width, 16], fill=(8, 8, 8, 255))
    ImageDraw.Draw(chrome_img).rectangle([0, height - 16, width, height], fill=(8, 8, 8, 255))
    assert chrome_img.getpixel((8, 8))[3] == 255
    assert chrome_img.getpixel((2, 2))[3] >= 200

    jpg = tmp_path / "atm.jpg"
    plate = tmp_path / "atm_plate.jpg"
    chrome = tmp_path / "atm_chrome.png"
    save_jpeg(plate_img, jpg)
    save_jpeg(plate_img, plate)
    save_png(chrome_img, chrome)
    profile = MotionProfile(
        style="parallax",
        quality="light",
        intensity=0.96,
        # Longer than the other ffmpeg tests: the post-fade sample frame needs
        # enough ease separation from the peak frame once edge-fade eats into
        # the low end of the pingpong curve (see edge_fade_frames).
        duration=3.0,
        fps=12,
        width=width,
        height=height,
        light_leak=True,
    )
    ok, msg = generate_motion(jpg, profile=profile, force=True, plate=plate, chrome=chrome)
    assert ok, msg
    mp4 = jpg.with_suffix(".mp4")
    peak = max_motion_frame(profile.frames)
    fade_frames = edge_fade_frames(profile.frames, profile.fps)
    first = _grab_frame(mp4, fade_frames, tmp_path / "atm0.png")
    moved = _grab_frame(mp4, peak, tmp_path / "atm_peak.png")

    # Locked letterbox / corner atmosphere.
    for sample in ((8, 6), (width // 2, 6), (width - 8, 6), (8, height - 6), (2, 2)):
        assert _channel_delta(first.getpixel(sample), moved.getpixel(sample)) <= 6, sample

    # Plate still Ken-Burns in the open center.
    center_delta = _channel_delta(first.getpixel((width // 2, height // 2)), moved.getpixel((width // 2, height // 2)))
    assert center_delta >= 8, center_delta


@pytest.mark.skipif(ffmpeg_bin() is None, reason="ffmpeg not installed")
def test_ffmpeg_uniform_plate_vignette_does_not_zoom(tmp_path: Path):
    """If vignette were burned into the plate, zoom would lighten the corners."""
    width, height = 320, 180
    plate_img = Image.new("RGB", (width, height), (200, 40, 80))
    layout = Layout(
        name="Vignette only",
        canvas_width=width,
        canvas_height=height,
        background=LayoutBackground(
            fade_left=0,
            fade_right=0,
            fade_top=0,
            fade_bottom=0,
            vignette=0.9,
            overlay_opacity=0,
            gradient_opacity=0,
        ),
        layers=[],
    )
    jpg = tmp_path / "vig.jpg"
    plate = tmp_path / "vig_plate.jpg"
    chrome = tmp_path / "vig_chrome.png"
    save_jpeg(plate_img, jpg)
    save_jpeg(plate_img, plate)
    save_png(render_chrome(MediaItem(title="Probe"), layout), chrome)
    profile = MotionProfile(
        style="parallax",
        quality="light",
        intensity=0.96,
        duration=1.0,
        fps=12,
        width=width,
        height=height,
        light_leak=True,
    )
    ok, msg = generate_motion(jpg, profile=profile, force=True, plate=plate, chrome=chrome)
    assert ok, msg
    peak = max_motion_frame(profile.frames)
    fade_frames = edge_fade_frames(profile.frames, profile.fps)
    first = _grab_frame(jpg.with_suffix(".mp4"), fade_frames, tmp_path / "vig0.png")
    moved = _grab_frame(jpg.with_suffix(".mp4"), peak, tmp_path / "vig_peak.png")
    for sample in ((2, 2), (8, 8), (20, 16), (width - 3, 2), (width // 2, 4)):
        assert _channel_delta(first.getpixel(sample), moved.getpixel(sample)) <= 4, sample


@pytest.mark.skipif(ffmpeg_bin() is None, reason="ffmpeg not installed")
def test_ffmpeg_kenburns_is_temporally_smooth(tmp_path: Path):
    """Adjacent-frame travel follows ping-pong speed — no duplicate/jump stutter."""
    width, height = 320, 180
    plate_img = _stripe_plate(width, height)
    jpg = tmp_path / "smooth.jpg"
    plate = tmp_path / "smooth_plate.jpg"
    chrome = tmp_path / "smooth_chrome.png"
    save_jpeg(plate_img, jpg)
    save_jpeg(plate_img, plate)
    save_png(Image.new("RGBA", (width, height), (0, 0, 0, 0)), chrome)
    profile = MotionProfile(
        style="kenburns",
        quality="light",
        intensity=0.96,
        duration=2.0,
        fps=24,
        width=width,
        height=height,
        light_leak=False,
    )
    ok, msg = generate_motion(jpg, profile=profile, force=True, plate=plate, chrome=chrome)
    assert ok, msg
    mp4 = jpg.with_suffix(".mp4")
    grabbed = [_grab_frame(mp4, n, tmp_path / f"sm{n}.png") for n in range(profile.frames)]

    def region_sad(a: Image.Image, b: Image.Image) -> int:
        ca = a.crop((48, 36, width - 48, height - 36))
        cb = b.crop((48, 36, width - 48, height - 36))
        return sum(abs(p - q) for p, q in zip(ca.tobytes(), cb.tobytes()))

    peak = max_motion_frame(profile.frames)
    span = region_sad(grabbed[0], grabbed[peak])
    assert span >= 50_000, span
    adjacent = [region_sad(grabbed[i], grabbed[i + 1]) for i in range(len(grabbed) - 1)]
    assert min(adjacent) > 0
    assert max(adjacent) < span
    assert sum(adjacent) / len(adjacent) <= span * 0.55
    join = region_sad(grabbed[0], grabbed[-1])
    assert join < span * 0.35
    # Speed envelope matches CSS ease-in-out (not zoompan stair-steps).
    speeds = [abs(math.sin(2 * math.pi * (i + 0.5) / profile.frames)) for i in range(len(adjacent))]
    mean_s = sum(adjacent) / len(adjacent)
    mean_v = sum(speeds) / len(speeds)
    num = sum((s - mean_s) * (v - mean_v) for s, v in zip(adjacent, speeds))
    den_s = math.sqrt(sum((s - mean_s) ** 2 for s in adjacent))
    den_v = math.sqrt(sum((v - mean_v) ** 2 for v in speeds))
    corr = num / (den_s * den_v)
    assert corr >= 0.93, corr


@pytest.mark.skipif(ffmpeg_bin() is None or ffprobe_bin() is None, reason="ffmpeg not installed")
def test_ffmpeg_loop_is_cfr_without_bframes_or_dupes(tmp_path: Path):
    """Player vs encoder: constant frame rate, no B-frames, no duplicate timestamps."""
    width, height = 320, 180
    plate_img = _stripe_plate(width, height)
    jpg = tmp_path / "cfr.jpg"
    plate = tmp_path / "cfr_plate.jpg"
    chrome = tmp_path / "cfr_chrome.png"
    save_jpeg(plate_img, jpg)
    save_jpeg(plate_img, plate)
    save_png(Image.new("RGBA", (width, height), (0, 0, 0, 0)), chrome)
    profile = MotionProfile(
        style="parallax",
        quality="light",
        intensity=0.55,
        duration=2.0,
        fps=30,
        width=width,
        height=height,
        light_leak=False,
    )
    ok, msg = generate_motion(jpg, profile=profile, force=True, plate=plate, chrome=chrome)
    assert ok, msg
    mp4 = jpg.with_suffix(".mp4")
    stream = _probe_stream(mp4)
    assert stream["codec_name"] == "h264"
    assert stream["profile"] == "Main"
    assert int(stream["level"]) == 40
    assert stream["pix_fmt"] == "yuv420p"
    assert stream["r_frame_rate"] == "30/1"
    assert stream["avg_frame_rate"] == "30/1"
    assert int(stream["has_b_frames"]) == 0
    assert int(stream.get("nb_frames") or 0) == profile.frames
    pts = _probe_frame_pts(mp4)
    assert len(pts) == profile.frames
    step = 1.0 / profile.fps
    deltas = [pts[i + 1] - pts[i] for i in range(len(pts) - 1)]
    assert all(abs(d - step) < 0.0008 for d in deltas), deltas[:8]
    assert all(d > 0 for d in deltas)


@pytest.mark.skipif(ffmpeg_bin() is None, reason="ffmpeg not installed")
def test_generate_motion_survives_exdev_promote(tmp_path: Path, monkeypatch):
    """Bake must promote /tmp → gallery even when os.rename raises EXDEV."""
    import errno
    import os

    item = MediaItem(title="EXDEV", year=2024)
    layout = PRESETS["Status Focus"]
    jpg = tmp_path / "gallery" / "exdev.jpg"
    plate = tmp_path / "gallery" / "exdev_plate.jpg"
    chrome = tmp_path / "gallery" / "exdev_chrome.png"
    jpg.parent.mkdir(parents=True)
    save_jpeg(render_still(item, layout), jpg)
    save_jpeg(render_plate(item, layout), plate)
    save_png(render_chrome(item, layout), chrome)
    profile = MotionProfile(
        style="kenburns",
        quality="light",
        intensity=0.5,
        duration=1.0,
        fps=12,
        width=320,
        height=180,
        light_leak=False,
    )

    def rename_exdev(a, b):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(os, "rename", rename_exdev)
    ok, msg = generate_motion(jpg, profile=profile, force=True, plate=plate, chrome=chrome)
    assert ok, msg
    assert has_motion(jpg)
