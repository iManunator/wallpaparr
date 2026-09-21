from app.chrome import chrome_pill_metrics, draw_chrome_pill, pill_padding
from app.render import _font
from app.seerr_status import seerr_badge, seerr_kind, seerr_label


def test_seerr_only_beats_requestable():
    badge = seerr_badge("seerr_only", "requestable", "jellyseerr")
    assert badge and badge["id"] == "seerr_only"
    assert badge["label"] == "Seerr only"
    assert seerr_kind("seerr_only", "requestable", "jellyseerr") == "seerr_only"
    assert seerr_label("seerr_only", "requestable", "jellyseerr") == "Seerr only"


def test_requestable_without_seerr_only():
    badge = seerr_badge("", "requestable", "tmdb")
    assert badge and badge["id"] == "requestable"
    assert badge["label"] == "Requestable"


def test_on_seerr_when_source_is_seerr_and_not_in_library():
    badge = seerr_badge("", "", "seerr")
    assert badge and badge["id"] == "on_seerr"
    assert badge["label"] == "On Seerr"


def test_in_library_hides_seerr_chrome():
    assert seerr_badge("in_library", "available", "jellyseerr") is None
    assert seerr_badge("in_library", "available", "jellyfin") is None
    assert seerr_kind("in_library", "available", "jellyfin") is None


def test_not_available_maps_to_requestable():
    assert seerr_kind("unknown", "not_available", "jellyfin") == "requestable"


def test_pill_padding_is_symmetric_and_scaled():
    pad_x, pad_y = pill_padding(22)
    assert pad_x >= 12
    assert pad_y >= 6
    assert pad_x > pad_y


def test_chrome_pill_centers_glyph_bbox():
    from PIL import Image, ImageDraw

    canvas = Image.new("RGBA", (400, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font(24)
    text = "Unwatched"
    metrics = chrome_pill_metrics(draw, text, font)
    left, top, right, bottom = metrics["bbox"]
    assert metrics["text_dx"] + left == metrics["pad_x"]
    assert metrics["width"] - (metrics["text_dx"] + right) == metrics["pad_x"]
    assert metrics["text_dy"] + top == metrics["pad_y"]
    assert metrics["height"] - (metrics["text_dy"] + bottom) == metrics["pad_y"]
    assert metrics["radius"] == metrics["height"] // 2
    box = draw_chrome_pill(draw, text, 10, 10, font, (122, 208, 196, 255))
    assert box[2] - box[0] == metrics["width"]
    assert box[3] - box[1] == metrics["height"]
