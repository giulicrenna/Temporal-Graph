import os
import xml.etree.ElementTree as ET

import pytest

from temporal_graph import Edge, TemporalGraph, render
from temporal_graph.figure import Figure

from .png_utils import SIGNATURE, decode_png

SVG_NS = "{http://www.w3.org/2000/svg}"
RED = (214, 39, 40)


@pytest.fixture
def graph():
    g = TemporalGraph(["alpha", "beta", "gamma"])
    g.add_snapshot(0, [Edge("alpha", "beta", color="#d62728")])
    g.add_snapshot(1, [Edge("alpha", "beta", color="#d62728", weight=3),
                       Edge("beta", "gamma", directed=True)])
    g.add_snapshot(2, [Edge("beta", "gamma", directed=True)])
    return g


def parse(figure):
    return ET.fromstring(figure.to_svg().split("\n", 1)[1])


def test_render_returns_figure(graph):
    figure = render(graph, "connections")
    assert isinstance(figure, Figure)
    assert figure.width > 0 and figure.height > 0
    assert "Figure(" in repr(figure)


def test_to_svg_is_valid_xml_with_declaration(graph):
    svg = render(graph, "decisions").to_svg()
    assert svg.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert parse(render(graph, "decisions")).tag == f"{SVG_NS}svg"


@pytest.mark.parametrize("mode", ["connections", "decisions"])
@pytest.mark.parametrize("scale", [1.0, 2.0])
def test_png_matches_figure_size(graph, tmp_path, mode, scale):
    figure = render(graph, mode)
    path = figure.savefig(tmp_path / "out.png", scale=scale)
    image = decode_png(open(path, "rb").read())
    assert image.width == round(figure.width * scale)
    assert image.height == round(figure.height * scale)


def test_png_contains_edge_color_labels_and_white_background(graph, tmp_path):
    figure = render(graph, "connections")
    image = decode_png(open(figure.savefig(tmp_path / "g.png"), "rb").read())
    assert image.pixel(0, 0) == (255, 255, 255)
    assert image.count(RED) > 50
    assert image.non_white(0, 0, 60, image.height) > 100


def test_bytes_and_file_agree(graph, tmp_path):
    figure = render(graph, "connections")
    path = figure.savefig(tmp_path / "g.png")
    assert open(path, "rb").read() == figure.to_png_bytes()
    assert figure.to_png_bytes()[:8] == SIGNATURE


def test_savefig_format_follows_extension_or_override(graph, tmp_path):
    figure = render(graph, "connections")
    svg_path = figure.savefig(tmp_path / "a.SVG")
    assert open(svg_path, encoding="utf-8").read().startswith("<?xml")
    forced = figure.savefig(tmp_path / "noext", format="png")
    assert open(forced, "rb").read(8) == SIGNATURE


def test_savefig_creates_directories_and_returns_absolute_path(graph, tmp_path):
    path = render(graph, "connections").savefig(str(tmp_path / "a" / "b" / "g.svg"))
    assert os.path.isabs(path) and os.path.exists(path)


def test_savefig_rejects_unknown_format(graph, tmp_path):
    figure = render(graph, "connections")
    with pytest.raises(ValueError, match="Unsupported format"):
        figure.savefig(tmp_path / "g.jpg")
    with pytest.raises(ValueError, match="Unsupported format"):
        figure.savefig(tmp_path / "g")


def test_unsupported_color_fails_clearly_on_png_only(tmp_path):
    g = TemporalGraph(["a", "b"])
    g.add_snapshot(0, [Edge("a", "b", color="not-a-color")])
    figure = render(g, "connections")
    figure.savefig(tmp_path / "ok.svg")
    with pytest.raises(ValueError, match="Unsupported color"):
        figure.savefig(tmp_path / "bad.png")


def test_render_with_path_keeps_legacy_behavior(graph, tmp_path):
    svg_path = render(graph, "connections", str(tmp_path / "g.svg"))
    assert isinstance(svg_path, str) and os.path.isabs(svg_path)
    assert ET.parse(svg_path).getroot().tag == f"{SVG_NS}svg"

    png_path = render(graph, "decisions", tmp_path / "g.png")
    assert open(png_path, "rb").read(8) == SIGNATURE

    other = render(graph, "decisions", str(tmp_path / "g.txt"))
    assert open(other, encoding="utf-8").read().startswith("<?xml")


def test_svg_uses_plain_shapes_without_markers(graph):
    root = parse(render(graph, "decisions"))
    assert root.find(f"{SVG_NS}defs") is None
    assert not [e for e in root.iter() if "marker-end" in e.attrib]
    assert root.find(f"{SVG_NS}polygon") is not None


def test_dashed_strokes_use_flat_caps(graph):
    root = parse(render(graph, "decisions"))
    dashed = [e for e in root.iter() if e.get("stroke-dasharray") in ("6 4",)]
    assert dashed
    assert all(e.get("stroke-linecap") == "butt" for e in dashed)


def test_content_stays_clear_of_node_labels():
    g = TemporalGraph(["a_very_long_node_name", "b", "c", "d"])
    g.add_snapshot(0, [Edge("a_very_long_node_name", "b"), Edge("b", "c"), Edge("c", "d"),
                       Edge("a_very_long_node_name", "d")])
    g.add_snapshot(1, [Edge("b", "d")])
    for mode in ("connections", "decisions"):
        root = parse(render(g, mode))
        lines = list(root.iter(f"{SVG_NS}line"))[: len(g.nodes)]
        line_start = min(float(e.get("x1")) for e in lines)
        label_right = max(float(t.get("x")) for t in root.iter(f"{SVG_NS}text")
                          if t.get("text-anchor") == "end")
        assert label_right < line_start
        last_node_y = max(float(e.get("y1")) for e in lines)
        circles = [
            float(c.get("cx")) - float(c.get("r"))
            for c in root.iter(f"{SVG_NS}circle")
            if float(c.get("cy")) <= last_node_y
        ]
        assert circles
        assert min(circles) >= line_start


def test_weight_labels_are_drawn_after_connections(graph):
    root = parse(render(graph, "connections"))
    children = list(root)
    divider = max(i for i, e in enumerate(children) if e.get("stroke") == "#cfcfcf")
    last_path = max(i for i, e in enumerate(children[:divider]) if e.tag == f"{SVG_NS}path")
    backing = [i for i, e in enumerate(children[:divider])
               if e.tag == f"{SVG_NS}rect" and i > 0 and e.get("fill") == "white"]
    assert backing and min(backing) > last_path


def test_decisions_draws_a_connection_line_for_every_drawn_edge(graph):
    root = parse(render(graph, "decisions"))
    children = list(root)
    divider = max(i for i, e in enumerate(children) if e.get("stroke") == "#cfcfcf")
    paths = [e for e in children[:divider] if e.tag == f"{SVG_NS}path"]

    snapshots = graph.snapshots()
    ghosts = len(snapshots[0][1])
    events = len(graph.change_events())
    unchanged = sum(
        len({e.key() for e in a} & {e.key() for e in b})
        for (_, a), (_, b) in zip(snapshots, snapshots[1:])
    )
    assert len(paths) == ghosts + events + unchanged
    faded = [p for p in paths if p.get("stroke-opacity")]
    assert len(faded) == unchanged


def test_png_honors_stroke_opacity(tmp_path):
    g = TemporalGraph(["a", "b"])
    g.add_snapshot(0, [Edge("a", "b", color="#ff0000")])
    g.add_snapshot(1, [Edge("a", "b", color="#ff0000")])
    image = decode_png(render(g, "decisions").to_png_bytes(scale=1))
    assert image.count((255, 0, 0), tolerance=10) > 0
    assert image.count((255, 153, 153), tolerance=25) > 10


def test_legend_is_english_and_fits(graph):
    root = parse(render(graph, "decisions"))
    texts = {t.text for t in root.iter(f"{SVG_NS}text")}
    expected = {"initial state", "lifeline", "connect", "unchanged", "disconnect", "weight > 1",
                "directed"}
    assert expected <= texts
    for t in root.iter(f"{SVG_NS}text"):
        assert float(t.get("y")) < float(root.get("height"))


def test_directed_connection_stops_at_arrow_base(graph):
    root = parse(render(graph, "connections"))
    polygons = list(root.iter(f"{SVG_NS}polygon"))
    assert polygons
    assert all(len(p.get("points").split()) == 3 for p in polygons)
