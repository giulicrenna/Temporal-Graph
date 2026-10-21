import xml.etree.ElementTree as ET

import pytest

from temporal_graph import Edge, TemporalGraph, render

SVG_NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture
def graph():
    g = TemporalGraph(["a", "b", "c"])
    g.add_snapshot(0, [Edge("a", "b")])
    g.add_snapshot(1, [Edge("a", "b", weight=3), Edge("b", "c", directed=True, color="#f00")])
    g.add_snapshot(2, [Edge("b", "c")])
    return g


@pytest.mark.parametrize("mode", ["connections", "decisions"])
def test_render_writes_valid_svg(graph, tmp_path, mode):
    out = tmp_path / "nested" / f"{mode}.svg"
    returned = render(graph, mode, str(out))
    assert returned == str(out.resolve())
    root = ET.parse(out).getroot()
    assert root.tag == f"{SVG_NS}svg"


@pytest.mark.parametrize("mode", ["connections", "decisions"])
def test_render_includes_node_labels(graph, tmp_path, mode):
    out = tmp_path / "g.svg"
    render(graph, mode, str(out))
    texts = {el.text for el in ET.parse(out).getroot().iter(f"{SVG_NS}text")}
    assert {"a", "b", "c"} <= texts


def test_invalid_mode(graph, tmp_path):
    with pytest.raises(ValueError, match="mode"):
        render(graph, "bogus", str(tmp_path / "g.svg"))


def test_empty_graph(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        render(TemporalGraph(["a", "b"]), "connections", str(tmp_path / "g.svg"))


@pytest.mark.parametrize("mode", ["connections", "decisions"])
def test_single_snapshot_and_single_node(tmp_path, mode):
    g = TemporalGraph(["a"])
    g.add_snapshot(0, [])
    render(g, mode, str(tmp_path / "g.svg"))
    assert (tmp_path / "g.svg").stat().st_size > 0


def test_output_is_deterministic(graph, tmp_path):
    first, second = tmp_path / "1.svg", tmp_path / "2.svg"
    render(graph, "decisions", str(first))
    render(graph, "decisions", str(second))
    assert first.read_bytes() == second.read_bytes()
