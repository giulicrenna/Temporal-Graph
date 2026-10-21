"""Renderer for :mod:`temporal_graph`.

Two visual modes are supported:

``connections`` — for each recorded timestep draw every active edge as a
vertical line at that timestep's x position (a full snapshot per
column).

``decisions`` — emphasise when edges appear and disappear. Each edge
that stays alive across multiple timesteps is drawn as a continuous
line spanning its lifetime, with markers at the endpoints. Edge
appearances (``"connect"``) are drawn as a solid line at the timestep
they appear; disappearances (``"disconnect"``) are drawn as a dashed
line at the timestep they vanish.

Per-edge properties (color, direction, weight) are honored by both
modes. Non-unit weight is rendered as a "snake" / sinusoidal
connection; directed edges get an arrowhead at the destination node
end. A small legend at the bottom explains the visual conventions.

:func:`render` returns a :class:`~temporal_graph.figure.Figure` that can be
saved as SVG or PNG without any external library.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Union, overload

from ._font import text_width
from .figure import Figure
from .graph import Edge, TemporalGraph

EdgeKey = Tuple[str, str]
Lanes = Dict[EdgeKey, int]


# Layout constants (user units == pixels at scale 1).


LEFT_PAD = 12.0           # space left of the node labels
LABEL_GAP = 12.0          # space between node labels and node lines
MARGIN_RIGHT = 50.0
MARGIN_TOP = 30.0
MARGIN_BOTTOM = 60.0      # room for timestep labels
MIN_WIDTH = 320.0
TIMESTEP_SPACING = 110.0  # horizontal distance between consecutive timesteps
NODE_SPACING = 70.0       # vertical distance between consecutive node lines
LANE_FRACTION = 0.40      # fraction of the timestep column reserved for sub-lanes
LANE_HALF_WIDTH = TIMESTEP_SPACING * LANE_FRACTION
LINE_THICKNESS = 3.0
TICK_THICKNESS = 1.0
DOT_RADIUS = 5.0
ARROW_LENGTH = 11.0
ARROW_HALF_WIDTH = 5.5
GRID_GREY = "#cfcfcf"     # timestep ticks
GHOST_GREY = "#9a9a9a"    # t=0 initial-state lines
INK = "#111111"
WHITE = "white"
FONT_FAMILY = "DejaVu Sans, Verdana, Arial, sans-serif"
NODE_FONT_SIZE = 18
STEP_FONT_SIZE = 16
LABEL_FONT_SIZE = 11      # weight labels
LEGEND_FONT_SIZE = 12
TEXT_CENTER_FACTOR = 0.36  # baseline offset from the visual center, in em
DISCONNECT_DASH = "6 4"
UNCHANGED_OPACITY = 0.4   # connections that persist from the previous timestep
TICK_DASH = "2 4"

# Legend geometry.
LEGEND_ROW_HEIGHT = 28.0
LEGEND_GLYPH_WIDTH = 28.0
LEGEND_GLYPH_HALF_HEIGHT = 9.0
LEGEND_TEXT_GAP = 8.0
LEGEND_ITEM_GAP = 22.0
LEGEND_TOP_GAP = 12.0
LEGEND_BOTTOM_GAP = 8.0

# Snake (wavy connection) parameters.
#
# The weight of an edge is a property *between* two nodes, so the
# snake wobbles the vertical connection line sideways, not the
# horizontal lifeline. Amplitude scales with the weight; default
# weight 1.0 gives a straight line.
SNAKE_AMPLITUDE_PER_WEIGHT = 4.0   # horizontal amplitude per (weight - 1)
SNAKE_HALF_PERIOD = 8.0            # vertical half-period of the wave


@dataclass(frozen=True)
class _Layout:
    label_right: float   # right edge of the node labels
    line_start: float    # left end of the node lines
    first_column: float  # x of the first timestep column
    x_max: float         # right end of the node lines
    width: float
    base_height: float   # height of the plot area, above the legend


def _make_layout(nodes: List[str], timestep_count: int) -> _Layout:
    label_width = max(text_width(n, NODE_FONT_SIZE) for n in nodes)
    label_right = LEFT_PAD + label_width
    line_start = label_right + LABEL_GAP
    first_column = line_start + LANE_HALF_WIDTH + DOT_RADIUS + 6.0
    x_max = first_column + (timestep_count - 1) * TIMESTEP_SPACING + TIMESTEP_SPACING / 2
    return _Layout(
        label_right=label_right,
        line_start=line_start,
        first_column=first_column,
        x_max=x_max,
        width=max(x_max + MARGIN_RIGHT, MIN_WIDTH),
        base_height=MARGIN_TOP + (len(nodes) - 1) * NODE_SPACING + MARGIN_BOTTOM,
    )



# Geometry helpers


def _node_y(idx: int) -> float:
    return MARGIN_TOP + idx * NODE_SPACING


def _snake_amplitude(weight: float) -> float:
    """Horizontal amplitude of the snake for a connection of this weight.

    Default weight 1.0 → amplitude 0 (straight line). Larger weights
    give a larger sideways wobble on the vertical connection.
    """
    if weight <= 1.0:
        return 0.0
    return (weight - 1.0) * SNAKE_AMPLITUDE_PER_WEIGHT


def _vertical_snake_path(x: float, y_top: float, y_bot: float, weight: float) -> str:
    """Return an SVG ``d`` attribute for a wavy vertical connection.

    The path runs from ``(x, y_top)`` to ``(x, y_bot)`` and wobbles
    sideways (in x) with amplitude proportional to ``weight``. The
    default weight 1.0 gives a perfectly straight vertical line.
    """
    height = y_bot - y_top
    amplitude = _snake_amplitude(weight)
    if height <= 0 or amplitude <= 0:
        return f"M {x:g} {y_top:g} L {x:g} {y_bot:g}"

    n_halves = max(2, int(round(height / SNAKE_HALF_PERIOD)))
    if n_halves % 2 != 0:
        n_halves += 1
    step = height / n_halves
    parts = [f"M {x:g} {y_top:g}"]
    direction = -1.0
    cy = y_top
    for _ in range(n_halves):
        x_peak = x + direction * amplitude
        parts.append(f"Q {x_peak:g} {cy + step / 2:g} {x:g} {cy + step:g}")
        cy += step
        direction = -direction
    return " ".join(parts)


def _lanes_for(keys: Set[EdgeKey]) -> Lanes:
    """Assign sub-lane indices to the given edge keys, sorted by key."""
    return {key: i for i, key in enumerate(sorted(keys))}


def _lane_x(x_center: float, lane: int, n_lanes: int) -> float:
    """Return the x for the given sub-lane within a timestep column."""
    if n_lanes <= 1:
        return x_center
    step = (2 * LANE_HALF_WIDTH) / n_lanes
    return x_center - LANE_HALF_WIDTH + (lane + 0.5) * step



# Public API


@overload
def render(graph: TemporalGraph, mode: str, path: None = None) -> Figure: ...


@overload
def render(graph: TemporalGraph, mode: str, path: Union[str, "os.PathLike[str]"]) -> str: ...


def render(
    graph: TemporalGraph,
    mode: str,
    path: Union[str, "os.PathLike[str]", None] = None,
) -> Union[Figure, str]:
    """Render ``graph`` and return a :class:`~temporal_graph.figure.Figure`.

    ``mode`` must be either ``"connections"`` or ``"decisions"``. Save the
    result with ``figure.savefig("graph.svg")`` or ``figure.savefig("graph.png")``.

    If ``path`` is given the figure is also saved there and the absolute
    path is returned instead of the figure. The format follows the file
    extension (``.png`` or ``.svg``); any other extension writes SVG.
    """
    if mode not in ("connections", "decisions"):
        raise ValueError(f"mode must be 'connections' or 'decisions', got {mode!r}")
    if not graph.timesteps:
        raise ValueError("Cannot render an empty TemporalGraph (no snapshots)")

    timesteps = graph.timesteps
    nodes = graph.nodes
    layout = _make_layout(nodes, len(timesteps))
    legend_rows = _pack_legend(mode, layout.width)
    legend_height = LEGEND_TOP_GAP + len(legend_rows) * LEGEND_ROW_HEIGHT + LEGEND_BOTTOM_GAP
    height = layout.base_height + 4 + legend_height

    svg = _make_svg(layout.width, height)
    _draw_node_lines(svg, layout, nodes)
    _draw_step_ticks(svg, layout, timesteps, len(nodes))

    if mode == "connections":
        _render_connections(svg, layout, graph, timesteps, nodes)
    else:
        _render_decisions(svg, layout, graph, timesteps, nodes)

    _draw_legend(svg, layout, legend_rows)

    figure = Figure(svg)
    if path is None:
        return figure
    extension = os.path.splitext(os.fspath(path))[1].lstrip(".").lower()
    return figure.savefig(path, format=extension if extension == "png" else "svg")



# SVG primitives


def _make_svg(width: float, height: float) -> ET.Element:
    svg = ET.Element(
        "svg",
        attrib={
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {width:g} {height:g}",
            "width": f"{width:g}",
            "height": f"{height:g}",
        },
    )
    ET.SubElement(
        svg,
        "rect",
        attrib={"x": "0", "y": "0", "width": f"{width:g}", "height": f"{height:g}", "fill": WHITE},
    )
    return svg


def _add_line(
    svg: ET.Element,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: str,
    width: float = LINE_THICKNESS,
    cap: str = "round",
    dash: Optional[str] = None,
) -> None:
    attrib = {
        "x1": f"{x1:g}",
        "y1": f"{y1:g}",
        "x2": f"{x2:g}",
        "y2": f"{y2:g}",
        "stroke": color,
        "stroke-width": f"{width:g}",
        "stroke-linecap": cap,
    }
    if dash:
        attrib["stroke-dasharray"] = dash
    ET.SubElement(svg, "line", attrib=attrib)


def _add_path(
    svg: ET.Element, d: str, color: str, dash: Optional[str] = None, opacity: float = 1.0
) -> None:
    # Dashed strokes use flat caps: round caps would close the gaps.
    attrib = {
        "d": d,
        "fill": "none",
        "stroke": color,
        "stroke-width": f"{LINE_THICKNESS:g}",
        "stroke-linecap": "butt" if dash else "round",
        "stroke-linejoin": "round",
    }
    if dash:
        attrib["stroke-dasharray"] = dash
    if opacity < 1.0:
        attrib["stroke-opacity"] = f"{opacity:g}"
    ET.SubElement(svg, "path", attrib=attrib)


def _add_circle(svg: ET.Element, cx: float, cy: float, r: float, color: str) -> None:
    ET.SubElement(
        svg,
        "circle",
        attrib={"cx": f"{cx:g}", "cy": f"{cy:g}", "r": f"{r:g}", "fill": color},
    )


def _add_arrow(svg: ET.Element, x: float, y_tip: float, color: str, pointing_down: bool) -> None:
    """Arrowhead whose tip is at ``(x, y_tip)``."""
    y_base = y_tip - ARROW_LENGTH if pointing_down else y_tip + ARROW_LENGTH
    points = (
        f"{x:g},{y_tip:g} "
        f"{x - ARROW_HALF_WIDTH:g},{y_base:g} "
        f"{x + ARROW_HALF_WIDTH:g},{y_base:g}"
    )
    ET.SubElement(svg, "polygon", attrib={"points": points, "fill": color})


def _add_text(
    svg: ET.Element,
    x: float,
    y_center: float,
    text: str,
    size: float,
    color: str,
    anchor: str = "start",
) -> None:
    """Text whose visual center is vertically at ``y_center``."""
    node = ET.SubElement(
        svg,
        "text",
        attrib={
            "x": f"{x:g}",
            "y": f"{y_center + size * TEXT_CENTER_FACTOR:g}",
            "font-family": FONT_FAMILY,
            "font-size": f"{size:g}",
            "fill": color,
            "text-anchor": anchor,
        },
    )
    node.text = text


def _add_weight_label(
    svg: ET.Element, x: float, y_center: float, weight: float, color: str
) -> None:
    """Label ``w=<weight>`` beside a connection, on a white backing.

    Only drawn when the weight differs from the default 1.0. The label sits
    clear of the snake's sideways wobble.
    """
    if weight == 1.0:
        return
    text = f"w={weight:g}"
    x_text = x + _snake_amplitude(weight) + DOT_RADIUS + 5.0
    pad = 3.0
    ET.SubElement(
        svg,
        "rect",
        attrib={
            "x": f"{x_text - pad:g}",
            "y": f"{y_center - LABEL_FONT_SIZE * 0.65:g}",
            "width": f"{text_width(text, LABEL_FONT_SIZE) + 2 * pad:g}",
            "height": f"{LABEL_FONT_SIZE * 1.3:g}",
            "fill": WHITE,
        },
    )
    _add_text(svg, x_text, y_center, text, LABEL_FONT_SIZE, color)


_WeightLabel = Tuple[float, float, float, str]  # x, y_center, weight, color


def _label_y(y_src: float, y_tgt: float) -> float:
    """Label height midway between the top node row and the next one."""
    return min(y_src, y_tgt) + NODE_SPACING / 2


def _draw_weight_labels(svg: ET.Element, labels: List[_WeightLabel]) -> None:
    """Draw labels last so no connection is painted over them."""
    for x, y_center, weight, color in labels:
        _add_weight_label(svg, x, y_center, weight, color)


def _add_endpoint(
    svg: ET.Element, x: float, y: float, color: str, arrow_down: Optional[bool]
) -> None:
    """A dot, or an arrowhead pointing down/up when ``arrow_down`` is not None."""
    if arrow_down is None:
        _add_circle(svg, x, y, DOT_RADIUS, color)
    else:
        _add_arrow(svg, x, y, color, pointing_down=arrow_down)


def _draw_connection(
    svg: ET.Element,
    x: float,
    y_src: float,
    y_tgt: float,
    color: str,
    weight: float,
    directed: bool,
    dash: Optional[str] = None,
    markers: bool = True,
    opacity: float = 1.0,
) -> None:
    """Vertical connection between two node rows, with optional end markers.

    A directed line always stops at the arrow base, so it never pokes through
    an arrowhead drawn at the target, whether drawn here or by the caller.
    """
    line_top, line_bot = min(y_src, y_tgt), max(y_src, y_tgt)
    arrow_down = y_tgt > y_src
    if directed:
        if arrow_down:
            line_bot -= ARROW_LENGTH
        else:
            line_top += ARROW_LENGTH
    path = _vertical_snake_path(x, line_top, line_bot, weight)
    _add_path(svg, path, color, dash, opacity)
    if markers:
        _add_endpoint(svg, x, y_src, color, None)
        _add_endpoint(svg, x, y_tgt, color, arrow_down if directed else None)



# Frame / chrome


def _draw_node_lines(svg: ET.Element, layout: _Layout, nodes: List[str]) -> None:
    for i, node in enumerate(nodes):
        y = _node_y(i)
        _add_line(svg, layout.line_start, y, layout.x_max, y, INK)
        _add_text(svg, layout.label_right, y, node, NODE_FONT_SIZE, INK, anchor="end")


def _draw_step_ticks(
    svg: ET.Element, layout: _Layout, timesteps: List[int], n_nodes: int
) -> None:
    base_y = _node_y(max(n_nodes - 1, 0)) + NODE_SPACING * 0.4
    for idx, t in enumerate(timesteps):
        x = layout.first_column + idx * TIMESTEP_SPACING
        _add_line(
            svg, x, MARGIN_TOP - 10, x, base_y + 10, GRID_GREY,
            width=TICK_THICKNESS, cap="butt", dash=TICK_DASH,
        )
        _add_text(svg, x, base_y + STEP_FONT_SIZE + 2, str(t), STEP_FONT_SIZE, INK, anchor="middle")



# Mode: connections (full snapshot per timestep)


def _render_connections(
    svg: ET.Element,
    layout: _Layout,
    graph: TemporalGraph,
    timesteps: List[int],
    nodes: List[str],
) -> None:
    weight_labelled: Set[EdgeKey] = set()
    labels: List[_WeightLabel] = []
    for col, t in enumerate(timesteps):
        x_center = layout.first_column + col * TIMESTEP_SPACING
        edges = graph.edges_at(t)
        lanes = _lanes_for({e.key() for e in edges})
        for edge in edges:
            key = edge.key()
            x = _lane_x(x_center, lanes[key], len(lanes))
            src, tgt = edge.endpoints_in_order()
            y_src = _node_y(nodes.index(src))
            y_tgt = _node_y(nodes.index(tgt))
            color = edge.effective_color()
            _draw_connection(svg, x, y_src, y_tgt, color, edge.weight, edge.directed)
            if edge.weight != 1.0 and key not in weight_labelled:
                weight_labelled.add(key)
                labels.append((x, _label_y(y_src, y_tgt), edge.weight, color))
    _draw_weight_labels(svg, labels)



# Mode: decisions (lifelines + connect/disconnect event marks)


def _decision_lanes(
    edges_by_t: Dict[int, Dict[EdgeKey, Edge]], timesteps: List[int]
) -> Dict[int, Lanes]:
    """One lane assignment per column, shared by lifelines and event marks.

    A column holds the edges alive at that timestep plus the edges that
    disconnect there, so no two drawn items of a column share a lane.
    """
    lanes: Dict[int, Lanes] = {}
    for i, t in enumerate(timesteps):
        keys = set(edges_by_t[t])
        if i > 0:
            keys |= set(edges_by_t[timesteps[i - 1]]) - keys
        lanes[t] = _lanes_for(keys)
    return lanes


def _render_decisions(
    svg: ET.Element,
    layout: _Layout,
    graph: TemporalGraph,
    timesteps: List[int],
    nodes: List[str],
) -> None:
    edges_by_t: Dict[int, Dict[EdgeKey, Edge]] = dict(graph._snapshots)
    lanes_by_t = _decision_lanes(edges_by_t, timesteps)

    def column_x(col: int, key: EdgeKey) -> float:
        lanes = lanes_by_t[timesteps[col]]
        return _lane_x(layout.first_column + col * TIMESTEP_SPACING, lanes[key], len(lanes))

    # 0) Initial state at t=0: every alive edge as a grey "ghost"
    #    connection without endpoint markers, so the column reads as a
    #    starting state.
    for key, edge in sorted(edges_by_t[timesteps[0]].items()):
        src, tgt = edge.endpoints_in_order()
        _draw_connection(
            svg, column_x(0, key), _node_y(nodes.index(src)), _node_y(nodes.index(tgt)),
            GHOST_GREY, edge.weight, directed=False, markers=False,
        )

    # 1) Lifelines between consecutive timesteps where the edge is
    #    alive at both ends. At the right end the unchanged connection is
    #    drawn faded, so it reads as "still there" without competing with
    #    the connect / disconnect events.
    weight_labelled: Set[EdgeKey] = set()
    labels: List[_WeightLabel] = []
    for col in range(len(timesteps) - 1):
        edges_a = edges_by_t[timesteps[col]]
        edges_b = edges_by_t[timesteps[col + 1]]
        for key in sorted(edges_a.keys() & edges_b.keys()):
            edge_a, edge_b = edges_a[key], edges_b[key]
            color = edge_a.effective_color()
            x_left, x_right = column_x(col, key), column_x(col + 1, key)
            ys = [_node_y(nodes.index(n)) for n in key]
            for y in ys:
                _add_line(svg, x_left, y, x_right, y, color)

            src, tgt = edge_b.endpoints_in_order()
            y_src, y_tgt = _node_y(nodes.index(src)), _node_y(nodes.index(tgt))
            color_b = edge_b.effective_color()
            _draw_connection(
                svg, x_right, y_src, y_tgt, color_b, edge_b.weight, edge_b.directed,
                markers=False, opacity=UNCHANGED_OPACITY,
            )
            _add_endpoint(svg, x_right, y_src, color_b, None)
            _add_endpoint(
                svg, x_right, y_tgt, color_b, (y_tgt > y_src) if edge_b.directed else None
            )

            if edge_a.weight != 1.0 and key not in weight_labelled:
                weight_labelled.add(key)
                labels.append((x_left, min(ys) - 12.0, edge_a.weight, color))

    # 2) Connect / disconnect event marks.
    events_by_t: Dict[int, List[Tuple[str, EdgeKey]]] = {}
    for t, kind, key in graph.change_events():
        events_by_t.setdefault(t, []).append((kind, key))
    for t, events in events_by_t.items():
        col = timesteps.index(t)
        for kind, key in sorted(events, key=lambda ev: (ev[1], ev[0])):
            ref_t = t if kind == "connect" else timesteps[col - 1]
            ref_edge = edges_by_t[ref_t][key]
            color = ref_edge.effective_color()
            src, tgt = ref_edge.endpoints_in_order()
            x = column_x(col, key)
            y_src, y_tgt = _node_y(nodes.index(src)), _node_y(nodes.index(tgt))
            _draw_connection(
                svg, x, y_src, y_tgt, color, ref_edge.weight, ref_edge.directed,
                dash=DISCONNECT_DASH if kind == "disconnect" else None,
            )
            if ref_edge.weight != 1.0 and key not in weight_labelled:
                weight_labelled.add(key)
                labels.append((x, _label_y(y_src, y_tgt), ref_edge.weight, color))
    _draw_weight_labels(svg, labels)



# Legend


LegendItem = Tuple[str, str, float]


def _legend_items(mode: str) -> List[Tuple[str, str]]:
    if mode == "connections":
        return [("connection", "connection"), ("snake", "weight > 1"), ("directed", "directed")]
    return [
        ("ghost", "initial state"),
        ("lifeline", "lifeline"),
        ("connect", "connect"),
        ("unchanged", "unchanged"),
        ("disconnect", "disconnect"),
        ("snake", "weight > 1"),
        ("directed", "directed"),
    ]


def _pack_legend(mode: str, width: float) -> List[List[LegendItem]]:
    """Greedy row packing of legend items using measured text widths."""
    available = width - 2 * LEFT_PAD
    rows: List[List[LegendItem]] = [[]]
    used = 0.0
    for kind, label in _legend_items(mode):
        item_width = LEGEND_GLYPH_WIDTH + LEGEND_TEXT_GAP + text_width(label, LEGEND_FONT_SIZE)
        needed = item_width if not rows[-1] else used + LEGEND_ITEM_GAP + item_width
        if rows[-1] and needed > available:
            rows.append([])
            needed = item_width
        rows[-1].append((kind, label, item_width))
        used = needed
    return rows


def _draw_legend(svg: ET.Element, layout: _Layout, rows: List[List[LegendItem]]) -> None:
    y_div = layout.base_height + 4
    _add_line(
        svg, LEFT_PAD, y_div, layout.width - LEFT_PAD, y_div, GRID_GREY,
        width=TICK_THICKNESS, cap="butt",
    )
    for row_index, row in enumerate(rows):
        y = y_div + LEGEND_TOP_GAP + (row_index + 0.5) * LEGEND_ROW_HEIGHT
        cursor = LEFT_PAD
        for kind, label, item_width in row:
            _draw_legend_glyph(svg, kind, cursor, y)
            _add_text(
                svg, cursor + LEGEND_GLYPH_WIDTH + LEGEND_TEXT_GAP, y, label,
                LEGEND_FONT_SIZE, INK,
            )
            cursor += item_width + LEGEND_ITEM_GAP


def _draw_legend_glyph(svg: ET.Element, kind: str, x: float, y: float) -> None:
    """Draw a small sample of the given visual element in a glyph box at ``x``."""
    center = x + LEGEND_GLYPH_WIDTH / 2
    top, bottom = y - LEGEND_GLYPH_HALF_HEIGHT, y + LEGEND_GLYPH_HALF_HEIGHT

    if kind == "connection":
        _draw_connection(svg, center, top, bottom, INK, 1.0, directed=False)
    elif kind == "snake":
        _draw_connection(svg, center, top, bottom, INK, 2.5, directed=False, markers=False)
    elif kind == "directed":
        _draw_connection(svg, center, top, bottom, INK, 1.0, directed=True)
    elif kind == "ghost":
        _draw_connection(svg, center, top, bottom, GHOST_GREY, 1.0, directed=False, markers=False)
    elif kind == "connect":
        _draw_connection(svg, center, top, bottom, INK, 1.0, directed=False, markers=False)
    elif kind == "unchanged":
        _draw_connection(
            svg, center, top, bottom, INK, 1.0, directed=False, markers=False,
            opacity=UNCHANGED_OPACITY,
        )
        _add_endpoint(svg, center, top, INK, None)
        _add_endpoint(svg, center, bottom, INK, None)
    elif kind == "disconnect":
        _draw_connection(
            svg, center, top, bottom, INK, 1.0, directed=False, dash=DISCONNECT_DASH,
            markers=False,
        )
    elif kind == "lifeline":
        _add_line(svg, x + 2, y, x + LEGEND_GLYPH_WIDTH - 2, y, INK)
    else:
        raise ValueError(f"Unknown legend glyph {kind!r}")
