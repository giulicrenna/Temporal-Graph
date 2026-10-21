import xml.etree.ElementTree as ET

import pytest

from temporal_graph._font import text_width
from temporal_graph._raster import (
    Canvas,
    dash_polyline,
    encode_png,
    parse_color,
    rasterize,
    render_png,
    stroke_polygons,
)

from .png_utils import decode_png

WHITE = (255, 255, 255)


def square(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def svg(*children, width=20, height=20):
    root = ET.Element("svg", {"viewBox": f"0 0 {width} {height}", "width": str(width),
                              "height": str(height)})
    for tag, attrib, text in children:
        ET.SubElement(root, tag, attrib).text = text
    return root


def image_of(root, scale=1.0):
    return decode_png(render_png(root, scale))


@pytest.mark.parametrize(
    "value, expected",
    [
        ("#f00", (255, 0, 0, 1.0)),
        ("#FF8000", (255, 128, 0, 1.0)),
        ("#00000080", (0, 0, 0, 128 / 255)),
        ("rgb(10, 20, 30)", (10, 20, 30, 1.0)),
        ("rgba(10 20 30 / 50%)", (10, 20, 30, 0.5)),
        ("rgb(100%, 0%, 0%)", (255, 0, 0, 1.0)),
        ("Steelblue", (70, 130, 180, 1.0)),
        ("white", (255, 255, 255, 1.0)),
    ],
)
def test_parse_color(value, expected):
    assert parse_color(value) == pytest.approx(expected)


@pytest.mark.parametrize("value", [None, "none", "transparent", ""])
def test_parse_color_no_paint(value):
    assert parse_color(value) is None


@pytest.mark.parametrize("value", ["#ggg", "#12345", "notacolor", "rgb(1,2)", "rgb(a,b,c)"])
def test_parse_color_rejects_invalid(value):
    with pytest.raises(ValueError, match="Unsupported color"):
        parse_color(value)


def test_fill_whole_pixels_is_exact():
    canvas = Canvas(6, 6, WHITE)
    canvas.fill([square(2, 2, 4, 4)], (0, 0, 0, 1.0))
    black = {(x, y) for y in range(6) for x in range(6)
             if tuple(canvas.pixels[(y * 6 + x) * 3:(y * 6 + x) * 3 + 3]) == (0, 0, 0)}
    assert black == {(2, 2), (3, 2), (2, 3), (3, 3)}
    assert tuple(canvas.pixels[0:3]) == WHITE


def test_fill_partial_pixel_is_antialiased():
    canvas = Canvas(4, 4, WHITE)
    canvas.fill([square(1.5, 0, 3, 4)], (0, 0, 0, 1.0))
    edge = canvas.pixels[(1 * 4 + 1) * 3]
    assert 110 <= edge <= 145


def test_fill_union_of_overlapping_same_orientation_shapes():
    canvas = Canvas(8, 4, WHITE)
    canvas.fill([square(1, 0, 5, 4), square(3, 0, 7, 4)], (0, 0, 0, 1.0))
    row = canvas.pixels[0:24]
    assert [row[x * 3] for x in range(8)] == [255, 0, 0, 0, 0, 0, 0, 255]


def test_fill_alpha_blends():
    canvas = Canvas(2, 2, WHITE)
    canvas.fill([square(0, 0, 2, 2)], (0, 0, 0, 0.5))
    assert abs(canvas.pixels[0] - 128) <= 1


def test_fill_clips_outside_canvas():
    canvas = Canvas(4, 4, WHITE)
    canvas.fill([square(-10, -10, 20, 20)], (0, 0, 0, 1.0))
    assert set(canvas.pixels) == {0}
    canvas.fill([square(100, 100, 120, 120)], (255, 0, 0, 1.0))
    assert set(canvas.pixels) == {0}


def test_stroke_polygons_cover_the_line():
    canvas = Canvas(12, 8, WHITE)
    canvas.fill(stroke_polygons([(1, 4), (11, 4)], 4.0, "butt"), (0, 0, 0, 1.0))
    assert canvas.pixels[(4 * 12 + 6) * 3] == 0
    assert canvas.pixels[(1 * 12 + 6) * 3] == 255
    assert canvas.pixels[(4 * 12 + 0) * 3] == 255


def test_round_cap_extends_past_the_endpoint():
    flat = Canvas(12, 8, WHITE)
    flat.fill(stroke_polygons([(4, 4), (8, 4)], 4.0, "butt"), (0, 0, 0, 1.0))
    round_ = Canvas(12, 8, WHITE)
    round_.fill(stroke_polygons([(4, 4), (8, 4)], 4.0, "round"), (0, 0, 0, 1.0))
    assert flat.pixels[(4 * 12 + 3) * 3] == 255
    assert round_.pixels[(4 * 12 + 3) * 3] < 100


def test_zero_length_stroke():
    assert stroke_polygons([(1, 1), (1, 1)], 2.0, "butt") == []
    assert len(stroke_polygons([(1, 1), (1, 1)], 2.0, "round")) == 1


def test_dash_polyline_lengths():
    pieces = dash_polyline([(0, 0), (20, 0)], [4, 4])
    assert pieces == [[(0, 0), (4, 0)], [(8, 0), (12, 0)], [(16, 0), (20, 0)]]


def test_dash_polyline_continues_across_corners():
    pieces = dash_polyline([(0, 0), (6, 0), (6, 6)], [4, 4])
    assert pieces[0] == [(0, 0), (4, 0)]
    assert pieces[1][0] == (8 - 2, 2) or pieces[1][-1] == (6, 2)


def test_dash_without_pattern_returns_whole_line():
    assert dash_polyline([(0, 0), (5, 0)], []) == [[(0, 0), (5, 0)]]


def test_rect_circle_polygon_line_and_path():
    root = svg(
        ("rect", {"x": "0", "y": "0", "width": "20", "height": "20", "fill": "white"}, None),
        ("rect", {"x": "0", "y": "0", "width": "5", "height": "5", "fill": "#ff0000"}, None),
        ("circle", {"cx": "12", "cy": "4", "r": "3", "fill": "#00ff00"}, None),
        ("polygon", {"points": "2,10 8,10 5,16", "fill": "#0000ff"}, None),
        ("line", {"x1": "0", "y1": "18", "x2": "20", "y2": "18", "stroke": "#000000",
                  "stroke-width": "2"}, None),
        ("path", {"d": "M 12 8 Q 16 12 12 16", "fill": "none", "stroke": "#ff00ff",
                  "stroke-width": "2"}, None),
    )
    image = image_of(root)
    assert image.pixel(2, 2) == (255, 0, 0)
    assert image.pixel(12, 4) == (0, 255, 0)
    assert image.pixel(5, 11) == (0, 0, 255)
    assert image.pixel(10, 18) == (0, 0, 0)
    assert image.pixel(18, 2) == WHITE
    assert image.count((255, 0, 255), tolerance=40) > 5


def test_dashed_line_has_gaps():
    root = svg(
        ("line", {"x1": "0", "y1": "10", "x2": "20", "y2": "10", "stroke": "#000000",
                  "stroke-width": "2", "stroke-dasharray": "4 4"}, None),
    )
    row = image_of(root).rows[10]
    shades = [row[x * 3] for x in range(20)]
    assert 0 in shades and 255 in shades


def test_text_is_drawn_and_anchored():
    def ink_columns(anchor):
        root = svg(
            ("text", {"x": "50", "y": "20", "font-size": "16", "fill": "#000000",
                      "text-anchor": anchor}, "Hi"),
            width=100,
            height=30,
        )
        image = image_of(root)
        columns = [x for x in range(100) if image.non_white(x, 0, x + 1, 30)]
        return min(columns), max(columns)

    start = ink_columns("start")
    middle = ink_columns("middle")
    end = ink_columns("end")
    assert start[0] >= 50
    assert middle[0] < 50 < middle[1]
    assert end[1] <= 50


def test_text_width_scales_with_size_and_handles_unknown_chars():
    assert text_width("abc", 20) == pytest.approx(2 * text_width("abc", 10))
    assert text_width("中", 10) == text_width("?", 10)


def test_non_ascii_latin_text_renders():
    root = svg(("text", {"x": "2", "y": "18", "font-size": "16", "fill": "#000000"},
                "ñandú"), width=80, height=24)
    assert image_of(root).non_white(0, 0, 80, 24) > 40


def test_scale_changes_pixel_size():
    root = svg(width=10, height=6)
    assert rasterize(root, 1.0)[:2] == (10, 6)
    assert rasterize(root, 2.5)[:2] == (25, 15)


def test_rasterize_errors():
    with pytest.raises(ValueError, match="scale"):
        rasterize(svg(), 0)
    with pytest.raises(ValueError, match="too large"):
        rasterize(svg(width=20000, height=20000), 1.0)
    with pytest.raises(ValueError, match="no usable size"):
        rasterize(ET.Element("svg"))
    bad = svg(("path", {"d": "M 0 0 C 1 1 2 2 3 3", "stroke": "black"}, None))
    with pytest.raises(ValueError, match="path command"):
        rasterize(bad)


def test_encode_png_round_trip():
    pixels = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 10, 20, 30])
    image = decode_png(encode_png(2, 2, pixels))
    assert (image.width, image.height) == (2, 2)
    assert image.pixel(1, 0) == (0, 255, 0)
    assert image.pixel(1, 1) == (10, 20, 30)
