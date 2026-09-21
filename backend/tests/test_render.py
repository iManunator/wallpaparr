from __future__ import annotations

from PIL import Image, ImageDraw

from app.layouts import PRESETS
from app.models import GradientStop, Layout, LayoutBackground, MediaItem
from app.providers.demo import DemoProvider
from app.render import (
    _fit_font,
    _fit_title,
    _font,
    _truncate,
    linear_gradient_rgba,
    render_chrome,
    render_plate,
    render_still,
    slot_text,
    synthetic_backdrop,
)


def test_render_still_is_full_hd():
    layout = PRESETS["Netflix Hero"]
    item = DemoProvider().list_items()[0]
    image = render_still(item, layout)
    assert image.size == (1920, 1080)
    assert image.mode == "RGB"


def test_all_presets_render():
    item = MediaItem(title="Probe", year=2024, overview="Test", rating=8.0, genres=["Drama"])
    for name, layout in PRESETS.items():
        image = render_still(item, layout)
        assert image.size[0] == 1920, name


def test_flagship_presets_include_watch_status():
    for name, layout in PRESETS.items():
        slots = {layer.slot for layer in layout.layers}
        assert "watch_status" in slots, name


def test_watch_status_renders_as_pill():
    item = MediaItem(title="Probe", year=2024, watch_state="partial", overview="Test", rating=8.0)
    image = render_still(item, PRESETS["Status Focus"])
    assert image.size == (1920, 1080)


def test_seerr_only_chrome_renders_on_flagship_layout():
    item = MediaItem(
        title="Signal Country",
        year=2023,
        watch_state="unwatched",
        library_state="seerr_only",
        availability="requestable",
        source="jellyseerr",
        overview="A radio host in the desert starts receiving tomorrow's news.",
        rating=7.6,
    )
    in_library = item.model_copy(update={"library_state": "in_library", "availability": "available", "source": "jellyfin"})
    layout = PRESETS["Netflix Hero"]
    seerr_chrome = render_chrome(item, layout)
    library_chrome = render_chrome(in_library, layout)
    assert seerr_chrome.tobytes() != library_chrome.tobytes()
    hidden = layout.model_copy(update={"show_seerr_badge": False})
    assert render_chrome(item, hidden).tobytes() == library_chrome.tobytes()


def test_truncate_clips_long_text_to_width_with_ellipsis():
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    font = _font(26, bold=False)
    long_text = "Science Fiction  ·  Action & Adventure  ·  Documentary  ·  Animation  ·  War & Politics"
    truncated = _truncate(draw, long_text, font, 340)
    bbox = draw.textbbox((0, 0), truncated, font=font)
    assert bbox[2] - bbox[0] <= 340
    assert truncated.endswith("…")
    assert _truncate(draw, "2024", font, 340) == "2024"


def test_fit_font_shrinks_moderately_long_title_to_fit():
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    long_title = "The Fellowship of the Ring"
    font = _fit_font(draw, long_title, 72, True, 860)
    bbox = draw.textbbox((0, 0), long_title, font=font)
    assert bbox[2] - bbox[0] <= 860
    # A title that already fits is returned unshrunk (same width either way).
    short_text = "Dune"
    fitted = _fit_font(draw, short_text, 72, True, 860)
    plain = _font(72, bold=True)
    fitted_bbox = draw.textbbox((0, 0), short_text, font=fitted)
    plain_bbox = draw.textbbox((0, 0), short_text, font=plain)
    assert fitted_bbox == plain_bbox


def test_fit_title_truncates_only_when_even_the_shrink_floor_overflows():
    """_fit_font shrinks down to a floor (half the base size) so text never
    goes illegibly small. An extreme title can still overflow at the floor —
    _fit_title then truncates with an ellipsis as a last resort, so the box
    is never exceeded either way. Long enough to overflow any font, including
    this environment's PIL default-bitmap-font fallback (no TTF on Windows)."""
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    extreme_title = "A Very Long Seerr Title That Would Never Fit At Full Size On Any TV Screen " * 4
    text, font = _fit_title(draw, extreme_title, 72, True, 860)
    bbox = draw.textbbox((0, 0), text, font=font)
    assert bbox[2] - bbox[0] <= 860
    assert text.endswith("…")


def test_moderately_long_seerr_title_is_never_truncated_with_ellipsis():
    item = MediaItem(
        title="The Fellowship of the Ring",
        year=2024,
        source="jellyseerr",
    )
    for name, layout in PRESETS.items():
        image = render_still(item, layout)
        assert image.size[0] == 1920, name
    assert slot_text(item, "title") == item.title
    assert "…" not in item.title


def test_render_never_crashes_on_extreme_titles():
    item = MediaItem(
        title="A Very Long Seerr Title That Would Never Fit At Full Size On Any TV Screen",
        year=2024,
        source="jellyseerr",
    )
    for name, layout in PRESETS.items():
        image = render_still(item, layout)
        assert image.size[0] == 1920, name


def test_media_type_slot_shows_movie_or_series():
    movie = MediaItem(title="A Movie", media_type="movie")
    series = MediaItem(title="A Series", media_type="tv")
    assert slot_text(movie, "media_type") == "Movie"
    assert slot_text(series, "media_type") == "Series"


def test_every_preset_includes_media_type_slot():
    for name, layout in PRESETS.items():
        slots = {layer.slot for layer in layout.layers}
        assert "media_type" in slots, name


def test_long_genre_list_never_exceeds_its_layer_width_on_any_preset():
    """Real Jellyfin/TMDB genre names ("Science Fiction", not "Sci-Fi") must
    not bleed into the next fixed-x chip (e.g. runtime) on any bundled preset."""
    item = MediaItem(
        title="Probe",
        year=2024,
        overview="Test",
        rating=8.0,
        genres=["Science Fiction", "Action & Adventure", "Documentary", "Animation", "War & Politics"],
        official_rating="PG-13",
        runtime="3h 45m",
    )
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for name, layout in PRESETS.items():
        for layer in layout.layers:
            if layer.slot not in ("genres", "runtime", "year", "age", "source", "media_type") or not layer.width:
                continue
            text = slot_text(item, layer.slot, layer.max_items)
            if not text:
                continue
            bold = layer.font_weight in ("bold", "black", "semibold")
            font = _font(layer.font_size, bold=bold)
            truncated = _truncate(draw, text, font, int(layer.width))
            bbox = draw.textbbox((0, 0), truncated, font=font)
            assert bbox[2] - bbox[0] <= layer.width, (name, layer.slot)


def test_projectivy_dock_keeps_safe_zone():
    layout = PRESETS["Projectivy Dock"]
    assert layout.background.fade_bottom >= 0.4
    title = next(layer for layer in layout.layers if layer.slot == "title")
    assert title.y >= 120
    assert title.y < 400


def test_linear_gradient_left_to_right():
    bg = LayoutBackground(
        fade_left=0,
        fade_right=0,
        fade_top=0,
        fade_bottom=0,
        gradient_type="linear",
        gradient_angle=90,
        gradient_opacity=1,
        gradient_stops=[
            GradientStop(color="#ff0000", position=0, opacity=1),
            GradientStop(color="#0000ff", position=1, opacity=1),
        ],
    )
    image = linear_gradient_rgba((64, 32), bg)
    left = image.getpixel((2, 16))
    right = image.getpixel((61, 16))
    assert left[0] > left[2]
    assert right[2] > right[0]


def test_chrome_vignette_darkens_corners():
    layout = Layout(
        name="Vignette",
        canvas_width=80,
        canvas_height=45,
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
    chrome = render_chrome(MediaItem(title="Probe"), layout)
    corner = chrome.getpixel((1, 1))[3]
    center = chrome.getpixel((40, 22))[3]
    assert corner > center
    assert corner >= 200


def test_letterbox_fade_edges_are_opaque():
    layout = Layout(
        name="Letterbox",
        canvas_width=80,
        canvas_height=45,
        background=LayoutBackground(
            fade_left=0.48,
            fade_right=0.04,
            fade_top=0.1,
            fade_bottom=0.42,
            vignette=0,
            overlay_opacity=0,
            gradient_opacity=0,
        ),
        layers=[],
    )
    chrome = render_chrome(MediaItem(title="Probe"), layout)
    assert chrome.getpixel((0, 22))[3] == 255
    assert chrome.getpixel((0, 0))[3] == 255
    assert chrome.getpixel((40, 44))[3] == 255
    assert chrome.getpixel((1, 1))[3] == 255
    assert chrome.getpixel((70, 22))[3] < 80


def test_plate_excludes_vignette_and_letterbox():
    layout = Layout(
        name="Atmosphere",
        canvas_width=64,
        canvas_height=36,
        background=LayoutBackground(
            fade_left=0.5,
            fade_bottom=0.4,
            fade_top=0.2,
            vignette=0.9,
            overlay_opacity=0,
            gradient_opacity=0,
        ),
        layers=[],
    )
    item = MediaItem(title="Probe")
    from PIL import Image
    import io

    art = Image.new("RGB", (64, 36), (200, 80, 40))
    buf = io.BytesIO()
    art.save(buf, "JPEG")
    plate = render_plate(item, layout, backdrop_bytes=buf.getvalue())
    chrome = render_chrome(item, layout)
    still = render_still(item, layout, backdrop_bytes=buf.getvalue())
    assert plate.getpixel((2, 2))[0] > 150
    assert still.getpixel((2, 2))[0] < plate.getpixel((2, 2))[0]
    assert chrome.getpixel((2, 2))[3] > 100


def test_demo_still_is_not_the_synthetic_fallback():
    item = DemoProvider().list_items()[0]
    layout = PRESETS["Netflix Hero"]
    painted = render_still(item, layout)
    synth = synthetic_backdrop(item.title, painted.size)
    assert painted.getpixel((1500, 360)) != synth.getpixel((1500, 360))


def test_slot_text_maps_jellyfin_style_metadata():
    item = MediaItem(
        title="From",
        year=2022,
        genres=["Science Fiction", "Horror", "Drama", "Thriller"],
        rating=8.494,
        official_rating="TV-MA",
        runtime="51m",
        overview="Nightmare town.",
        source="jellyfin",
    )
    assert slot_text(item, "year") == "2022"
    assert slot_text(item, "genres", max_items=3) == "Science Fiction  ·  Horror  ·  Drama"
    assert slot_text(item, "rating") == "★ 8.5"
    assert slot_text(item, "age") == "TV-MA"
    assert slot_text(item, "runtime") == "51m"
    assert slot_text(item, "overview") == "Nightmare town."
    chrome = render_chrome(item, PRESETS["Netflix Hero"])
    empty = render_chrome(MediaItem(title="From"), PRESETS["Netflix Hero"])
    assert chrome.tobytes() != empty.tobytes()


def test_slot_text_maps_omdb_fields():
    item = MediaItem(
        title="Enriched",
        imdb_rating=8.4,
        rotten_tomatoes=92,
        metacritic=81,
        awards="Won 1 Oscar",
    )
    assert slot_text(item, "imdb_rating") == "IMDb 8.4"
    assert slot_text(item, "rotten_tomatoes") == "🍅 92%"
    assert slot_text(item, "metacritic") == "MC 81"
    assert slot_text(item, "awards") == "Won 1 Oscar"
    empty = MediaItem(title="Bare")
    assert slot_text(empty, "imdb_rating") == ""
    assert slot_text(empty, "rotten_tomatoes") == ""
    assert slot_text(empty, "metacritic") == ""
    assert slot_text(empty, "awards") == ""
