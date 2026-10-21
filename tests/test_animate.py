import io
import xml.etree.ElementTree as ET

import pytest

from temporal_graph import Animation, Edge, TemporalGraph, animate
from temporal_graph.animate import GLOW_OPACITY, INACTIVE_GREY, edge_width

from .png_utils import SIGNATURE

SVG_NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture
def graph():
    g = TemporalGraph(["a", "b", "c", "d"])
    g.add_snapshot(0, [Edge("a", "b"), Edge("b", "c")])
    g.add_snapshot(1, [Edge("a", "b", directed=True, weight=2.5, color="#d62728"),
                       Edge("a", "c")])
    g.add_snapshot(5, [Edge("a", "c")])
    return g


def frame_root(animation, index):
    return ET.fromstring(animation.frames[index].to_svg().split("\n", 1)[1])


def texts(root):
    return [t.text for t in root.iter(f"{SVG_NS}text")]


def test_one_frame_per_timestep_with_fixed_size(graph):
    animation = animate(graph)
    assert isinstance(animation, Animation)
    assert len(animation) == 3
    assert animation.timesteps == [0, 1, 5]
    sizes = {(f.width, f.height) for f in animation.frames}
    assert len(sizes) == 1
    assert "3 frames" in repr(animation)


def test_header_and_summary(graph):
    animation = animate(graph)
    first, second, last = (texts(frame_root(animation, i)) for i in range(3))
    assert "t = 0" in first and "t = 1" in second and "t = 5" in last
    assert "2 edges, 1 new, 1 removed" in second
    assert "1 edge, 0 new, 1 removed" in last


def test_first_frame_has_no_change_marks(graph):
    root = frame_root(animate(graph), 0)
    lines = list(root.iter(f"{SVG_NS}line"))
    # only the legend samples are dashed / glowing
    assert len([e for e in lines if e.get("stroke-dasharray")]) == 1
    assert len([e for e in lines if e.get("stroke-opacity")]) == 1


def test_new_removed_and_directed_edges(graph):
    root = frame_root(animate(graph), 1)
    glow = f"{GLOW_OPACITY:g}"
    glows = [e for e in root.iter(f"{SVG_NS}line") if e.get("stroke-opacity") == glow]
    dashed = [e for e in root.iter(f"{SVG_NS}line") if e.get("stroke-dasharray")]
    # one new edge (a-c) plus the legend sample; one removed edge (b-c) plus the legend sample
    assert len(glows) == 2
    assert len(dashed) == 2
    arrows = [p for p in root.iter(f"{SVG_NS}polygon") if p.get("fill") == "#d62728"]
    assert len(arrows) == 1
    assert "w=2.5" in texts(root)
    red = [e for e in root.iter(f"{SVG_NS}line") if e.get("stroke") == "#d62728"]
    assert {e.get("stroke-width") for e in red} == {f"{edge_width(2.5):g}"}


def test_isolated_nodes_are_greyed(graph):
    root = frame_root(animate(graph), 2)
    grey_rings = [c for c in root.iter(f"{SVG_NS}circle") if c.get("fill") == INACTIVE_GREY]
    assert len(grey_rings) == 2  # b and d are isolated at t=5


def test_edge_width_is_monotonic_and_clamped():
    assert edge_width(0) < edge_width(1) < edge_width(2) < edge_width(4)
    assert edge_width(1000) == edge_width(10_000)


def test_save_gif(graph, tmp_path):
    image_module = pytest.importorskip("PIL.Image")
    animation = animate(graph, frame_duration=300, loop=2)
    path = animation.save(tmp_path / "sub" / "evolution.gif", scale=1.0)
    image = image_module.open(path)
    assert image.n_frames == 3
    assert image.size == (round(animation.frames[0].width), round(animation.frames[0].height))
    assert image.info["duration"] == 300
    assert image.info["loop"] == 2


def test_gif_bytes_match_file(graph, tmp_path):
    animation = animate(graph)
    path = animation.save(tmp_path / "g.gif", scale=1.0)
    assert open(path, "rb").read() == animation.to_gif_bytes(scale=1.0)
    assert animation.to_gif_bytes(scale=1.0)[:6] == b"GIF89a"


def test_frames_can_be_saved_as_stills(graph, tmp_path):
    path = animate(graph).frames[1].savefig(tmp_path / "t1.png")
    assert open(path, "rb").read(8) == SIGNATURE


def test_single_node_and_single_snapshot(tmp_path):
    g = TemporalGraph(["solo"])
    g.add_snapshot(0, [])
    animation = animate(g)
    assert len(animation) == 1
    assert animation.to_gif_bytes()[:6] == b"GIF89a"


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"frame_duration": 10}, "frame_duration"),
        ({"frame_duration": 50.5}, "frame_duration"),
        ({"loop": -1}, "loop"),
        ({"loop": 70000}, "loop"),
    ],
)
def test_animate_validation(graph, kwargs, message):
    with pytest.raises(ValueError, match=message):
        animate(graph, **kwargs)


def test_empty_graph_and_bad_extension(graph, tmp_path):
    with pytest.raises(ValueError, match="empty"):
        animate(TemporalGraph(["a"]))
    with pytest.raises(ValueError, match=".gif"):
        animate(graph).save(tmp_path / "x.png")


def test_frames_property_is_a_copy(graph):
    animation = animate(graph)
    animation.frames.clear()
    assert len(animation) == 3


def node_centers(root):
    """Centers of the outer node rings (radius NODE_RADIUS + stroke / 2)."""
    from temporal_graph.animate import NODE_RADIUS, NODE_STROKE

    ring = f"{NODE_RADIUS + NODE_STROKE / 2:g}"
    return [(float(c.get("cx")), float(c.get("cy")))
            for c in root.iter(f"{SVG_NS}circle") if c.get("r") == ring]


def test_custom_positions_keep_shape_and_spacing():
    from temporal_graph.animate import MIN_NODE_DISTANCE

    g = TemporalGraph(["1", "2", "3"])
    g.add_snapshot(0, [Edge("1", "2", directed=True), Edge("1", "3", directed=True)])
    animation = animate(g, positions={"1": (1, 0), "2": (0, 2), "3": (2, 2)})
    (x1, y1), (x2, y2), (x3, y3) = node_centers(frame_root(animation, 0))
    assert x2 < x1 < x3 and y1 < y2 == y3
    assert x1 - x2 == pytest.approx(x3 - x1)
    closest = min(abs(x3 - x2), ((x1 - x2) ** 2 + (y2 - y1) ** 2) ** 0.5)
    assert closest == pytest.approx(MIN_NODE_DISTANCE)


def test_short_labels_go_inside_and_long_ones_below():
    from temporal_graph.animate import INSIDE_FONT_SIZE

    short = TemporalGraph(["1", "22"])
    short.add_snapshot(0, [Edge("1", "22")])
    root = frame_root(animate(short, positions={"1": (0, 0), "22": (1, 1)}), 0)
    centers = node_centers(root)
    labels = {t.text: t for t in root.iter(f"{SVG_NS}text") if t.text in ("1", "22")}
    assert {t.get("font-size") for t in labels.values()} == {f"{INSIDE_FONT_SIZE:g}"}
    assert float(labels["1"].get("x")) == pytest.approx(centers[0][0])

    long_names = TemporalGraph(["alpha", "beta"])
    long_names.add_snapshot(0, [Edge("alpha", "beta")])
    root = frame_root(animate(long_names, positions={"alpha": (0, 0), "beta": (1, 0)}), 0)
    (ax, ay), _ = node_centers(root)
    alpha = next(t for t in root.iter(f"{SVG_NS}text") if t.text == "alpha")
    assert float(alpha.get("x")) == pytest.approx(ax)
    assert float(alpha.get("y")) > ay


@pytest.mark.parametrize(
    "positions, message",
    [
        ({"a": (0, 0)}, "missing"),
        ({"a": (0, 0), "b": (0, 0), "c": (1, 1), "d": (2, 2)}, "distinct"),
    ],
)
def test_custom_positions_validation(graph, positions, message):
    with pytest.raises(ValueError, match=message):
        animate(graph, positions=positions)


def test_frame_is_valid_svg(graph):
    data = animate(graph).frames[0].to_svg()
    assert ET.parse(io.StringIO(data)).getroot().tag == f"{SVG_NS}svg"
