"""Pure-Python rasterizer for the SVG subset that ``temporal_graph`` emits.

Supported elements: ``rect``, ``line``, ``path`` (absolute ``M L Q Z``),
``circle``, ``polygon`` and ``text``. Shapes are anti-aliased with exact
horizontal coverage and a few vertical sub-scanlines, and PNG files are
written with ``zlib`` only.
"""

from __future__ import annotations

import math
import re
import struct
import xml.etree.ElementTree as ET
import zlib
from typing import Dict, List, Optional, Sequence, Tuple

from ._colors import NAMED_COLORS
from ._font import text_contours

Point = Tuple[float, float]
Polygon = List[Point]
Color = Tuple[int, int, int, float]

SUBSAMPLES = 4
MAX_PIXELS = 100_000_000
_PATH_TOKEN = re.compile(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_HEX_DIGITS = frozenset("0123456789abcdef")



# Colors


def parse_color(value: Optional[str]) -> Optional[Color]:
    """Parse a CSS color. Returns ``None`` for ``none`` / ``transparent``."""
    if value is None:
        return None
    text = value.strip().lower()
    if text in ("", "none", "transparent"):
        return None
    if text.startswith("#"):
        digits = text[1:]
        if len(digits) in (3, 4):
            digits = "".join(c * 2 for c in digits)
        if len(digits) not in (6, 8) or not set(digits) <= _HEX_DIGITS:
            raise ValueError(f"Unsupported color {value!r}")
        red, green, blue = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
        alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
        return (red, green, blue, alpha)
    if text.startswith(("rgb(", "rgba(")) and text.endswith(")"):
        parts = [p for p in re.split(r"[,\s/]+", text[text.index("(") + 1:-1]) if p]
        if len(parts) not in (3, 4):
            raise ValueError(f"Unsupported color {value!r}")
        try:
            channels = [_channel(p) for p in parts[:3]]
            alpha = _alpha(parts[3]) if len(parts) == 4 else 1.0
        except ValueError:
            raise ValueError(f"Unsupported color {value!r}") from None
        return (channels[0], channels[1], channels[2], alpha)
    if text in NAMED_COLORS:
        red, green, blue = NAMED_COLORS[text]
        return (red, green, blue, 1.0)
    raise ValueError(f"Unsupported color {value!r}")


def _channel(token: str) -> int:
    number = float(token[:-1]) * 2.55 if token.endswith("%") else float(token)
    return max(0, min(255, round(number)))


def _alpha(token: str) -> float:
    number = float(token[:-1]) / 100 if token.endswith("%") else float(token)
    return max(0.0, min(1.0, number))



# Canvas


class Canvas:
    """RGB pixel buffer with anti-aliased polygon filling."""

    def __init__(self, width: int, height: int, background: Tuple[int, int, int]) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(bytes(background) * (width * height))

    def clear(self, color: Tuple[int, int, int]) -> None:
        self.pixels[:] = bytes(color) * (self.width * self.height)

    def fill(self, polygons: Sequence[Sequence[Point]], color: Color) -> None:
        """Fill ``polygons`` together using the non-zero winding rule."""
        red, green, blue, alpha = color
        width = self.width
        crossings = self._collect_crossings(polygons)
        if not crossings:
            return

        weight = 1.0 / SUBSAMPLES
        coverage = [0.0] * (width + 2)
        delta = [0.0] * (width + 2)
        pixels = self.pixels
        for row in range(min(crossings) // SUBSAMPLES, max(crossings) // SUBSAMPLES + 1):
            lo, hi = width + 1, -1
            for sub in range(SUBSAMPLES):
                hits = crossings.get(row * SUBSAMPLES + sub)
                if not hits:
                    continue
                hits.sort()
                winding = 0
                start = 0.0
                for x, direction in hits:
                    if winding == 0:
                        start = x
                    winding += direction
                    if winding != 0:
                        continue
                    left, right = max(start, 0.0), min(x, float(width))
                    if right <= left:
                        continue
                    first, last = int(left), int(right)
                    if first == last:
                        coverage[first] += (right - left) * weight
                    else:
                        coverage[first] += (first + 1 - left) * weight
                        coverage[last] += (right - last) * weight
                        delta[first + 1] += weight
                        delta[last] -= weight
                    lo, hi = min(lo, first), max(hi, last)
            if hi < 0:
                continue

            running = 0.0
            base = row * width * 3
            for x in range(lo, min(hi, width - 1) + 1):
                running += delta[x]
                covered = coverage[x] + running
                if covered > 0.003:
                    blend = min(covered, 1.0) * alpha
                    i = base + x * 3
                    pixels[i] = int(pixels[i] + (red - pixels[i]) * blend + 0.5)
                    pixels[i + 1] = int(pixels[i + 1] + (green - pixels[i + 1]) * blend + 0.5)
                    pixels[i + 2] = int(pixels[i + 2] + (blue - pixels[i + 2]) * blend + 0.5)
            end = hi + 2
            coverage[lo:end] = [0.0] * (end - lo)
            delta[lo:end] = [0.0] * (end - lo)

    def _collect_crossings(
        self, polygons: Sequence[Sequence[Point]]
    ) -> Dict[int, List[Tuple[float, int]]]:
        """Edge crossings per sub-scanline index, as ``(x, winding direction)``."""
        limit = self.height * SUBSAMPLES
        edges: List[Tuple[float, float, int, int, int]] = []
        first, last = limit, 0
        for polygon in polygons:
            count = len(polygon)
            if count < 3:
                continue
            for i in range(count):
                x0, y0 = polygon[i]
                x1, y1 = polygon[(i + 1) % count]
                if y0 == y1:
                    continue
                direction = 1
                if y0 > y1:
                    x0, y0, x1, y1 = x1, y1, x0, y0
                    direction = -1
                k_start = max(math.ceil(y0 * SUBSAMPLES - 0.5), 0)
                k_end = min(math.ceil(y1 * SUBSAMPLES - 0.5), limit)
                if k_start >= k_end:
                    continue
                first, last = min(first, k_start), max(last, k_end)
                slope = (x1 - x0) / (y1 - y0)
                x_start = x0 + ((k_start + 0.5) / SUBSAMPLES - y0) * slope
                edges.append((x_start, slope / SUBSAMPLES, k_start, k_end, direction))

        crossings: Dict[int, List[Tuple[float, int]]] = {}
        buckets: List[List[Tuple[float, int]]] = [[] for _ in range(max(last - first, 0))]
        for x, step, k_start, k_end, direction in edges:
            for k in range(k_start, k_end):
                buckets[k - first].append((x, direction))
                x += step
        for offset, bucket in enumerate(buckets):
            if bucket:
                crossings[first + offset] = bucket
        return crossings



# Geometry


def _orient(polygon: Polygon) -> Optional[Polygon]:
    """Return ``polygon`` with positive signed area, or ``None`` if degenerate."""
    area = 0.0
    for i, (x0, y0) in enumerate(polygon):
        x1, y1 = polygon[(i + 1) % len(polygon)]
        area += x0 * y1 - x1 * y0
    if abs(area) < 1e-9:
        return None
    return polygon if area > 0 else polygon[::-1]


def _circle(cx: float, cy: float, radius: float) -> Polygon:
    segments = max(12, min(96, int(radius * 3) + 8))
    return [
        (cx + radius * math.cos(2 * math.pi * i / segments),
         cy + radius * math.sin(2 * math.pi * i / segments))
        for i in range(segments)
    ]


def stroke_polygons(points: Sequence[Point], width: float, cap: str) -> List[Polygon]:
    """Outline an open polyline as polygons that union under the non-zero rule."""
    path: List[Point] = []
    for point in points:
        if not path or point != path[-1]:
            path.append(point)
    half = width / 2
    if len(path) == 1:
        return [_circle(path[0][0], path[0][1], half)] if cap == "round" else []

    shapes: List[Polygon] = []
    normals: List[Point] = []
    last = len(path) - 2
    for i in range(len(path) - 1):
        (x0, y0), (x1, y1) = path[i], path[i + 1]
        length = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        nx, ny = -uy * half, ux * half
        normals.append((nx, ny))
        if cap == "square":
            if i == 0:
                x0, y0 = x0 - ux * half, y0 - uy * half
            if i == last:
                x1, y1 = x1 + ux * half, y1 + uy * half
        shapes.append([
            (x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny),
        ])

    for i in range(1, len(path) - 1):
        vx, vy = path[i]
        (ax, ay), (bx, by) = normals[i - 1], normals[i]
        for sign in (1.0, -1.0):
            shapes.append([
                (vx, vy), (vx + sign * ax, vy + sign * ay), (vx + sign * bx, vy + sign * by),
            ])

    if cap == "round":
        shapes.append(_circle(path[0][0], path[0][1], half))
        shapes.append(_circle(path[-1][0], path[-1][1], half))

    oriented = (_orient(shape) for shape in shapes)
    return [shape for shape in oriented if shape is not None]


def dash_polyline(points: Sequence[Point], pattern: Sequence[float]) -> List[List[Point]]:
    """Split a polyline into the "on" pieces of a dash pattern."""
    if not pattern or sum(pattern) <= 0:
        return [list(points)]
    cycle = list(pattern) if len(pattern) % 2 == 0 else list(pattern) * 2

    pieces: List[List[Point]] = []
    index = 0
    remaining = cycle[0]
    drawing = True
    current: List[Point] = [points[0]]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        if length == 0:
            continue
        position = 0.0
        while length - position > remaining:
            position += remaining
            t = position / length
            cut = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            if drawing:
                current.append(cut)
                pieces.append(current)
                current = []
            else:
                current = [cut]
            drawing = not drawing
            index = (index + 1) % len(cycle)
            remaining = cycle[index]
        remaining -= length - position
        if drawing:
            current.append((x1, y1))
    if drawing and len(current) > 1:
        pieces.append(current)
    return pieces



# SVG tree -> canvas


class _Renderer:
    def __init__(self, canvas: Canvas, scale_x: float, scale_y: float) -> None:
        self.canvas = canvas
        self.sx = scale_x
        self.sy = scale_y
        self.stroke_scale = (scale_x + scale_y) / 2

    def draw(self, element: ET.Element) -> None:
        tag = element.tag.rsplit("}", 1)[-1]
        handler = getattr(self, f"_draw_{tag}", None)
        if handler is not None:
            handler(element)

    def _device(self, x: float, y: float) -> Point:
        return (x * self.sx, y * self.sy)

    def _number(self, element: ET.Element, name: str, default: float = 0.0) -> float:
        raw = element.get(name)
        return default if raw is None else float(raw)

    def _paint(
        self, element: ET.Element, attribute: str, default: Optional[str]
    ) -> Optional[Color]:
        """Color of ``fill`` or ``stroke`` with ``opacity`` and ``<attribute>-opacity`` applied."""
        color = parse_color(element.get(attribute, default))
        if color is None:
            return None
        opacity = self._number(element, "opacity", 1.0) * self._number(
            element, f"{attribute}-opacity", 1.0
        )
        alpha = color[3] * max(0.0, min(1.0, opacity))
        return None if alpha <= 0 else (color[0], color[1], color[2], alpha)

    def _fill_color(self, element: ET.Element) -> Optional[Color]:
        return self._paint(element, "fill", "black")

    def _stroke(self, element: ET.Element, polylines: Sequence[Sequence[Point]]) -> None:
        color = self._paint(element, "stroke", None)
        if color is None:
            return
        width = self._number(element, "stroke-width", 1.0) * self.stroke_scale
        if width <= 0:
            return
        cap = element.get("stroke-linecap", "butt")
        dashes = [
            float(v) * self.stroke_scale
            for v in re.split(r"[,\s]+", element.get("stroke-dasharray", "").strip())
            if v
        ]
        shapes: List[Polygon] = []
        for polyline in polylines:
            pieces = dash_polyline(polyline, dashes) if dashes else [list(polyline)]
            for piece in pieces:
                shapes.extend(stroke_polygons(piece, width, cap))
        self.canvas.fill(shapes, color)

    def _draw_rect(self, element: ET.Element) -> None:
        color = self._fill_color(element)
        if color is None:
            return
        x, y = self._number(element, "x"), self._number(element, "y")
        w, h = self._number(element, "width"), self._number(element, "height")
        left, top = self._device(x, y)
        right, bottom = self._device(x + w, y + h)
        covers_canvas = (
            left <= 0 and top <= 0
            and right >= self.canvas.width and bottom >= self.canvas.height
        )
        if covers_canvas and color[3] >= 1.0:
            self.canvas.clear(color[:3])
            return
        self.canvas.fill([[(left, top), (right, top), (right, bottom), (left, bottom)]], color)

    def _draw_line(self, element: ET.Element) -> None:
        start = self._device(self._number(element, "x1"), self._number(element, "y1"))
        end = self._device(self._number(element, "x2"), self._number(element, "y2"))
        self._stroke(element, [[start, end]])

    def _draw_circle(self, element: ET.Element) -> None:
        color = self._fill_color(element)
        if color is None:
            return
        cx, cy = self._device(self._number(element, "cx"), self._number(element, "cy"))
        radius = self._number(element, "r") * self.stroke_scale
        self.canvas.fill([_circle(cx, cy, radius)], color)

    def _draw_polygon(self, element: ET.Element) -> None:
        color = self._fill_color(element)
        if color is None:
            return
        numbers = [float(v) for v in re.split(r"[,\s]+", element.get("points", "").strip()) if v]
        points = [self._device(numbers[i], numbers[i + 1]) for i in range(0, len(numbers) - 1, 2)]
        self.canvas.fill([points], color)

    def _draw_path(self, element: ET.Element) -> None:
        subpaths = self._subpaths(element.get("d", ""))
        color = self._fill_color(element)
        if color is not None:
            self.canvas.fill([points for points in subpaths if len(points) >= 3], color)
        self._stroke(element, [points for points in subpaths if len(points) >= 2])

    def _draw_text(self, element: ET.Element) -> None:
        color = self._fill_color(element)
        content = element.text or ""
        if color is None or not content:
            return
        contours = text_contours(
            content,
            self._number(element, "x"),
            self._number(element, "y"),
            self._number(element, "font-size", 16.0),
            element.get("text-anchor", "start"),
        )
        scaled = [[self._device(x, y) for x, y in contour] for contour in contours]
        self.canvas.fill(scaled, color)

    def _subpaths(self, data: str) -> List[List[Point]]:
        tokens = _PATH_TOKEN.findall(data)
        subpaths: List[List[Point]] = []
        current: List[Point] = []
        i = 0
        command = ""
        while i < len(tokens):
            if tokens[i].isalpha():
                command = tokens[i]
                i += 1
                if command in "Zz":
                    if current:
                        subpaths.append(current)
                        current = []
                    continue
            if command in ("M", "L"):
                point = self._device(float(tokens[i]), float(tokens[i + 1]))
                i += 2
                if command == "M":
                    if current:
                        subpaths.append(current)
                    current = [point]
                    command = "L"
                else:
                    current.append(point)
            elif command == "Q":
                values = [float(t) for t in tokens[i:i + 4]]
                i += 4
                control = self._device(values[0], values[1])
                end = self._device(values[2], values[3])
                current.extend(_flatten_quadratic(current[-1], control, end))
            else:
                raise ValueError(f"Unsupported path command {command!r}")
        if current:
            subpaths.append(current)
        return subpaths


def _flatten_quadratic(start: Point, control: Point, end: Point) -> List[Point]:
    span = math.hypot(control[0] - start[0], control[1] - start[1]) + math.hypot(
        end[0] - control[0], end[1] - control[1]
    )
    steps = max(4, min(48, int(span / 2)))
    points = []
    for step in range(1, steps + 1):
        t = step / steps
        u = 1.0 - t
        points.append((
            u * u * start[0] + 2 * u * t * control[0] + t * t * end[0],
            u * u * start[1] + 2 * u * t * control[1] + t * t * end[1],
        ))
    return points


def rasterize(root: ET.Element, scale: float = 2.0) -> Tuple[int, int, bytes]:
    """Rasterize an SVG element tree. Returns ``(width, height, rgb_bytes)``."""
    if scale <= 0:
        raise ValueError(f"scale must be positive, got {scale!r}")
    view_box = root.get("viewBox")
    if view_box:
        _, _, view_w, view_h = (float(v) for v in view_box.split())
    else:
        view_w, view_h = float(root.get("width", "0")), float(root.get("height", "0"))
    if view_w <= 0 or view_h <= 0:
        raise ValueError("SVG has no usable size")

    width, height = max(1, round(view_w * scale)), max(1, round(view_h * scale))
    if width * height > MAX_PIXELS:
        raise ValueError(f"Image of {width}x{height} pixels is too large; lower scale")

    canvas = Canvas(width, height, (255, 255, 255))
    renderer = _Renderer(canvas, width / view_w, height / view_h)
    for element in root:
        renderer.draw(element)
    return width, height, bytes(canvas.pixels)



# PNG


def encode_png(width: int, height: int, rgb: bytes) -> bytes:
    """Encode 8-bit RGB pixels as a PNG file."""
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        checksum = zlib.crc32(body) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + body + struct.pack(">I", checksum)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + chunk(b"IEND", b"")
    )


def render_png(root: ET.Element, scale: float = 2.0) -> bytes:
    """Rasterize an SVG element tree to PNG bytes."""
    return encode_png(*rasterize(root, scale))
