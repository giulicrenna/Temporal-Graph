"""Animated node-link view of a :class:`~temporal_graph.graph.TemporalGraph`.

Each frame shows the graph at one recorded timestep: nodes sit on a fixed
circle, edges that appear are highlighted, edges that carry on are drawn
normally and edges that disappear are shown as dashed grey ghosts. Weight is
encoded as line thickness and direction as an arrowhead.
"""

from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from ._font import text_width
from ._gif import encode_gif
from ._raster import rasterize
from .figure import Figure
from .graph import Edge, TemporalGraph
from .render import (
    DISCONNECT_DASH,
    GHOST_GREY,
    GRID_GREY,
    INK,
    WHITE,
    _add_circle,
    _add_line,
    _add_text,
    _make_svg,
)

Point = Tuple[float, float]
PathLike = Union[str, "os.PathLike[str]"]

DEFAULT_FRAME_DURATION_MS = 800
MIN_FRAME_DURATION_MS = 20
DEFAULT_GIF_SCALE = 1.5

PAD = 16.0
NODE_RADIUS = 14.0
NODE_STROKE = 2.0
NODE_GAP = 24.0             # free arc between neighbouring nodes on the ring
MIN_RING_RADIUS = 110.0
MIN_NODE_DISTANCE = 2 * NODE_RADIUS + NODE_GAP  # for user-supplied positions
LABEL_GAP = 8.0
NODE_FONT_SIZE = 16
INSIDE_FONT_SIZE = 12      # labels drawn inside the node circle
HEADER_FONT_SIZE = 20
SUMMARY_FONT_SIZE = 13
SMALL_FONT_SIZE = 11
LEGEND_FONT_SIZE = 12
HEADER_HEIGHT = 46.0
TIMELINE_HEIGHT = 52.0
LEGEND_ROW_HEIGHT = 24.0
LEGEND_GLYPH_WIDTH = 30.0
LEGEND_TEXT_GAP = 8.0
LEGEND_ITEM_GAP = 20.0
MIN_WIDTH = 360.0
INACTIVE_GREY = "#b0b0b0"
SUMMARY_GREY = "#666666"
GLOW_EXTRA_WIDTH = 7.0
GLOW_OPACITY = 0.25
REMOVED_WIDTH = 2.0
MIN_EDGE_WIDTH = 1.5
MAX_EDGE_WIDTH = 12.0


def edge_width(weight: float) -> float:
    """Stroke width for a weight; weight 1.0 matches the timeline renderer."""
    return max(MIN_EDGE_WIDTH, min(MAX_EDGE_WIDTH, 1.5 + 1.5 * weight))


@dataclass(frozen=True)
class _Layout:
    width: float
    height: float
    center: Point
    ring_radius: float
    positions: Dict[str, Point]
    timeline_y: float
    legend_top: float
    legend_rows: List[List[Tuple[str, str, float]]]
    label_style: str = "radial"  # "radial" (circle), "inside" or "below" the node


LEGEND_ITEMS = [
    ("new", "new"),
    ("unchanged", "unchanged"),
    ("removed", "removed"),
    ("directed", "directed"),
    ("weight", "weight = thickness"),
]


def _make_layout(nodes: List[str]) -> _Layout:
    count = len(nodes)
    ring = max(MIN_RING_RADIUS, count * (2 * NODE_RADIUS + NODE_GAP) / (2 * math.pi))
    label_width = max(text_width(n, NODE_FONT_SIZE) for n in nodes)
    half_x = ring + NODE_RADIUS + LABEL_GAP + label_width + PAD
    half_y = ring + NODE_RADIUS + LABEL_GAP + NODE_FONT_SIZE + PAD
    width = max(2 * half_x, MIN_WIDTH)
    center = (width / 2, HEADER_HEIGHT + half_y)

    positions: Dict[str, Point] = {}
    for i, node in enumerate(nodes):
        if count == 1:
            positions[node] = center
            continue
        angle = -math.pi / 2 + 2 * math.pi * i / count
        positions[node] = (center[0] + ring * math.cos(angle), center[1] + ring * math.sin(angle))

    return _finish_layout(width, 2 * half_y, center, ring, positions, "radial")


def _make_custom_layout(nodes: List[str], coordinates: Mapping[str, Point]) -> _Layout:
    """Fit user coordinates so the closest two nodes are ``MIN_NODE_DISTANCE`` apart."""
    missing = [n for n in nodes if n not in coordinates]
    if missing:
        raise ValueError(f"positions is missing nodes: {missing}")
    points = {n: (float(coordinates[n][0]), float(coordinates[n][1])) for n in nodes}
    values = list(points.values())
    if len(set(values)) != len(values):
        raise ValueError("positions must be distinct for every node")

    closest = min(
        (
            math.hypot(a[0] - b[0], a[1] - b[1])
            for i, a in enumerate(values)
            for b in values[i + 1:]
        ),
        default=1.0,
    )
    scale = MIN_NODE_DISTANCE / closest
    xs = [x * scale for x, _ in values]
    ys = [y * scale for _, y in values]
    inside_room = 2 * (NODE_RADIUS - NODE_STROKE) - 4
    inside = all(text_width(n, INSIDE_FONT_SIZE) <= inside_room for n in nodes)
    label_half = 0.0 if inside else max(text_width(n, NODE_FONT_SIZE) for n in nodes) / 2
    side = PAD + max(NODE_RADIUS, label_half)
    top = PAD + NODE_RADIUS
    bottom = PAD + NODE_RADIUS + (0.0 if inside else LABEL_GAP + NODE_FONT_SIZE)
    plot_width = max(xs) - min(xs) + 2 * side
    plot_height = max(ys) - min(ys) + top + bottom
    width = max(plot_width, MIN_WIDTH)
    dx = (width - plot_width) / 2 + side - min(xs)
    dy = HEADER_HEIGHT + top - min(ys)
    positions = {n: (x * scale + dx, y * scale + dy) for n, (x, y) in points.items()}
    center = (width / 2, HEADER_HEIGHT + plot_height / 2)
    style = "inside" if inside else "below"
    return _finish_layout(width, plot_height, center, 0.0, positions, style)


def _finish_layout(
    width: float,
    plot_height: float,
    center: Point,
    ring: float,
    positions: Dict[str, Point],
    label_style: str,
) -> _Layout:
    timeline_y = HEADER_HEIGHT + plot_height + TIMELINE_HEIGHT / 2
    rows = _pack_legend(width)
    legend_top = HEADER_HEIGHT + plot_height + TIMELINE_HEIGHT
    height = legend_top + len(rows) * LEGEND_ROW_HEIGHT + PAD / 2
    return _Layout(
        width, height, center, ring, positions, timeline_y, legend_top, rows, label_style
    )


def _pack_legend(width: float) -> List[List[Tuple[str, str, float]]]:
    available = width - 2 * PAD
    rows: List[List[Tuple[str, str, float]]] = [[]]
    used = 0.0
    for kind, label in LEGEND_ITEMS:
        item = LEGEND_GLYPH_WIDTH + LEGEND_TEXT_GAP + text_width(label, LEGEND_FONT_SIZE)
        needed = item if not rows[-1] else used + LEGEND_ITEM_GAP + item
        if rows[-1] and needed > available:
            rows.append([])
            needed = item
        rows[-1].append((kind, label, item))
        used = needed
    return rows



# Drawing


def _add_segment(
    svg: ET.Element,
    start: Point,
    end: Point,
    color: str,
    width: float,
    dash: Optional[str] = None,
    opacity: float = 1.0,
) -> None:
    attrib = {
        "x1": f"{start[0]:g}",
        "y1": f"{start[1]:g}",
        "x2": f"{end[0]:g}",
        "y2": f"{end[1]:g}",
        "stroke": color,
        "stroke-width": f"{width:g}",
        "stroke-linecap": "butt" if dash else "round",
    }
    if dash:
        attrib["stroke-dasharray"] = dash
    if opacity < 1.0:
        attrib["stroke-opacity"] = f"{opacity:g}"
    ET.SubElement(svg, "line", attrib=attrib)


def _add_arrow(svg: ET.Element, tip: Point, direction: Point, color: str, width: float) -> Point:
    """Arrowhead at ``tip`` pointing along unit ``direction``; returns its base."""
    length = 10.0 + 1.5 * width
    half = 5.0 + 0.75 * width
    ux, uy = direction
    base = (tip[0] - ux * length, tip[1] - uy * length)
    left = (base[0] - uy * half, base[1] + ux * half)
    right = (base[0] + uy * half, base[1] - ux * half)
    points = " ".join(f"{x:g},{y:g}" for x, y in (tip, left, right))
    ET.SubElement(svg, "polygon", attrib={"points": points, "fill": color})
    return base


def _draw_edge(
    svg: ET.Element,
    layout: _Layout,
    edge: Edge,
    color: str,
    width: float,
    dash: Optional[str] = None,
    glow: bool = False,
) -> None:
    src, tgt = edge.endpoints_in_order()
    (x0, y0), (x1, y1) = layout.positions[src], layout.positions[tgt]
    length = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    start = (x0 + ux * NODE_RADIUS, y0 + uy * NODE_RADIUS)
    end = (x1 - ux * (NODE_RADIUS + 1), y1 - uy * (NODE_RADIUS + 1))

    if glow:
        _add_segment(svg, start, end, color, width + GLOW_EXTRA_WIDTH, opacity=GLOW_OPACITY)
    line_end = end
    if edge.directed and not dash:
        line_end = _add_arrow(svg, end, (ux, uy), color, width)
    _add_segment(svg, start, line_end, color, width, dash)


def _draw_weight_label(svg: ET.Element, layout: _Layout, edge: Edge, color: str) -> None:
    (x0, y0), (x1, y1) = layout.positions[edge.u], layout.positions[edge.v]
    length = math.hypot(x1 - x0, y1 - y0)
    nx, ny = -(y1 - y0) / length, (x1 - x0) / length
    offset = edge_width(edge.weight) / 2 + 13.0
    x = (x0 + x1) / 2 + nx * offset
    y = (y0 + y1) / 2 + ny * offset
    text = f"w={edge.weight:g}"
    text_w = text_width(text, SMALL_FONT_SIZE)
    ET.SubElement(svg, "rect", attrib={
        "x": f"{x - text_w / 2 - 3:g}",
        "y": f"{y - SMALL_FONT_SIZE * 0.65:g}",
        "width": f"{text_w + 6:g}",
        "height": f"{SMALL_FONT_SIZE * 1.3:g}",
        "fill": WHITE,
    })
    _add_text(svg, x, y, text, SMALL_FONT_SIZE, color, anchor="middle")


def _draw_node(svg: ET.Element, layout: _Layout, node: str, active: bool) -> None:
    x, y = layout.positions[node]
    color = INK if active else INACTIVE_GREY
    ET.SubElement(svg, "circle", attrib={
        "cx": f"{x:g}", "cy": f"{y:g}", "r": f"{NODE_RADIUS + NODE_STROKE / 2:g}", "fill": color,
    })
    ET.SubElement(svg, "circle", attrib={
        "cx": f"{x:g}", "cy": f"{y:g}", "r": f"{NODE_RADIUS - NODE_STROKE / 2:g}", "fill": WHITE,
    })

    if layout.label_style == "inside":
        _add_text(svg, x, y, node, INSIDE_FONT_SIZE, color, anchor="middle")
        return
    cx, cy = layout.center
    if layout.label_style == "below" or (x, y) == (cx, cy):
        _add_text(svg, x, y + NODE_RADIUS + LABEL_GAP + NODE_FONT_SIZE / 2, node,
                  NODE_FONT_SIZE, color, anchor="middle")
        return
    cos, sin = (x - cx) / layout.ring_radius, (y - cy) / layout.ring_radius
    reach = NODE_RADIUS + LABEL_GAP
    anchor = "start" if cos > 0.3 else "end" if cos < -0.3 else "middle"
    lift = NODE_FONT_SIZE / 2 if anchor == "middle" else 0.0
    _add_text(svg, x + cos * reach, y + sin * (reach + lift), node, NODE_FONT_SIZE, color, anchor)


def _draw_header(svg: ET.Element, layout: _Layout, t: int, counts: Tuple[int, int, int]) -> None:
    y = HEADER_HEIGHT / 2 + 4
    _add_text(svg, PAD, y, f"t = {t}", HEADER_FONT_SIZE, INK)
    active, new, removed = counts
    summary = f"{active} edge{'' if active == 1 else 's'}, {new} new, {removed} removed"
    _add_text(svg, layout.width - PAD, y, summary, SUMMARY_FONT_SIZE, SUMMARY_GREY, anchor="end")


def _draw_timeline(svg: ET.Element, layout: _Layout, timesteps: List[int], current: int) -> None:
    y = layout.timeline_y
    left, right = PAD + 10, layout.width - PAD - 10
    _add_line(svg, left, y, right, y, GRID_GREY, width=2.0)
    count = len(timesteps)
    xs = [left + (right - left) * (i / (count - 1) if count > 1 else 0.5) for i in range(count)]
    spacing = (right - left) / max(count - 1, 1)
    widest = max(text_width(str(t), SMALL_FONT_SIZE) for t in timesteps)
    label_all = spacing >= widest + 6
    for i, (x, t) in enumerate(zip(xs, timesteps)):
        if i <= current:
            _add_circle(svg, x, y, 4.0, INK if i == current else SUMMARY_GREY)
        else:
            _add_circle(svg, x, y, 4.0, GRID_GREY)
        if label_all or i in (0, count - 1, current):
            color = INK if i == current else SUMMARY_GREY
            _add_text(svg, x, y + 16, str(t), SMALL_FONT_SIZE, color, anchor="middle")
    _add_circle(svg, xs[current], y, 7.0, INK)
    if current > 0:
        _add_line(svg, left, y, xs[current], y, INK, width=2.0)
        _add_circle(svg, xs[current], y, 7.0, INK)


def _draw_legend(svg: ET.Element, layout: _Layout) -> None:
    for row_index, row in enumerate(layout.legend_rows):
        y = layout.legend_top + (row_index + 0.5) * LEGEND_ROW_HEIGHT
        cursor = PAD
        for kind, label, item_width in row:
            start, end = (cursor + 2, y), (cursor + LEGEND_GLYPH_WIDTH - 2, y)
            if kind == "new":
                _add_segment(svg, start, end, INK, 3 + GLOW_EXTRA_WIDTH, opacity=GLOW_OPACITY)
                _add_segment(svg, start, end, INK, 3)
            elif kind == "unchanged":
                _add_segment(svg, start, end, INK, 3)
            elif kind == "removed":
                _add_segment(svg, start, end, GHOST_GREY, REMOVED_WIDTH, DISCONNECT_DASH)
            elif kind == "directed":
                base = _add_arrow(svg, end, (1.0, 0.0), INK, 3)
                _add_segment(svg, start, base, INK, 3)
            else:
                _add_segment(svg, start, end, INK, edge_width(3.0))
            _add_text(svg, cursor + LEGEND_GLYPH_WIDTH + LEGEND_TEXT_GAP, y, label,
                      LEGEND_FONT_SIZE, INK)
            cursor += item_width + LEGEND_ITEM_GAP


def _frame(graph: TemporalGraph, layout: _Layout, index: int) -> Figure:
    snapshots = graph.snapshots()
    timesteps = graph.timesteps
    t, edges = snapshots[index]
    current = {e.key(): e for e in edges}
    previous = {e.key(): e for e in snapshots[index - 1][1]} if index > 0 else current

    new_keys = sorted(current.keys() - previous.keys())
    removed_keys = sorted(previous.keys() - current.keys())
    kept_keys = sorted(current.keys() & previous.keys())

    svg = _make_svg(layout.width, layout.height)
    _draw_header(svg, layout, t, (len(current), len(new_keys), len(removed_keys)))

    for key in removed_keys:
        _draw_edge(svg, layout, previous[key], GHOST_GREY, REMOVED_WIDTH, dash=DISCONNECT_DASH)
    for key in kept_keys:
        edge = current[key]
        _draw_edge(svg, layout, edge, edge.effective_color(), edge_width(edge.weight))
    for key in new_keys:
        edge = current[key]
        _draw_edge(svg, layout, edge, edge.effective_color(), edge_width(edge.weight), glow=True)

    active = {n for key in current for n in key}
    for node in graph.nodes:
        _draw_node(svg, layout, node, node in active)
    for key in kept_keys + new_keys:
        edge = current[key]
        if edge.weight != 1.0:
            _draw_weight_label(svg, layout, edge, edge.effective_color())

    _draw_timeline(svg, layout, timesteps, index)
    _draw_legend(svg, layout)
    return Figure(svg)



# Public API


class Animation:
    """Frames of a temporal graph, one per recorded timestep, savable as GIF."""

    def __init__(self, frames: Sequence[Figure], timesteps: Sequence[int],
                 frame_duration: int, loop: int) -> None:
        self._frames = list(frames)
        self.timesteps = list(timesteps)
        self.frame_duration = frame_duration
        self.loop = loop

    @property
    def frames(self) -> List[Figure]:
        """One :class:`~temporal_graph.figure.Figure` per timestep."""
        return list(self._frames)

    def __len__(self) -> int:
        return len(self._frames)

    def to_gif_bytes(self, scale: float = DEFAULT_GIF_SCALE) -> bytes:
        """Encode all frames as an animated GIF at ``scale`` pixels per unit."""
        rasters = [rasterize(frame._root, scale) for frame in self._frames]
        return encode_gif(rasters, delay_cs=round(self.frame_duration / 10), loop=self.loop)

    def save(self, path: PathLike, scale: float = DEFAULT_GIF_SCALE) -> str:
        """Write a ``.gif`` file and return its absolute path."""
        abs_path = os.path.abspath(os.fspath(path))
        if os.path.splitext(abs_path)[1].lower() != ".gif":
            raise ValueError("Animations are saved as .gif; use frames[i].savefig() for stills")
        data = self.to_gif_bytes(scale)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as fh:
            fh.write(data)
        return abs_path

    def __repr__(self) -> str:
        return f"Animation({len(self)} frames, {self.frame_duration} ms each)"


def animate(
    graph: TemporalGraph,
    frame_duration: int = DEFAULT_FRAME_DURATION_MS,
    loop: int = 0,
    positions: Optional[Mapping[str, Point]] = None,
) -> Animation:
    """Build a node-link :class:`Animation` with one frame per timestep.

    ``frame_duration`` is in milliseconds (GIF stores hundredths of a second).
    ``loop`` is how many times the GIF repeats; 0 loops forever.

    Nodes sit on a circle unless ``positions`` maps every node to ``(x, y)``
    in any unit, with y pointing down. Those coordinates are scaled uniformly
    so the two closest nodes do not overlap. Labels are drawn inside the
    nodes when every label fits there, otherwise below them.
    """
    if not graph.timesteps:
        raise ValueError("Cannot animate an empty TemporalGraph (no snapshots)")
    if not isinstance(frame_duration, int) or frame_duration < MIN_FRAME_DURATION_MS:
        raise ValueError(f"frame_duration must be an int >= {MIN_FRAME_DURATION_MS} ms")
    if not isinstance(loop, int) or not 0 <= loop <= 0xFFFF:
        raise ValueError("loop must be an int between 0 and 65535")

    if positions is None:
        layout = _make_layout(graph.nodes)
    else:
        layout = _make_custom_layout(graph.nodes, positions)
    frames = [_frame(graph, layout, i) for i in range(len(graph.timesteps))]
    return Animation(frames, graph.timesteps, frame_duration, loop)
