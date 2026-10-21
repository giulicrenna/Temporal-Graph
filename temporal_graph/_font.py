"""Text metrics and glyph outlines for the built-in renderers."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import List, Tuple

from ._font_data import ADVANCES, OUTLINES, UNITS_PER_EM

Point = Tuple[float, float]
Contour = List[Point]

FALLBACK_CHAR = "?"
_TOKEN = re.compile(r"[MLQZ]|-?\d+")
_CURVE_STEPS = 6


def _resolve(char: str) -> str:
    return char if char in ADVANCES else FALLBACK_CHAR


def text_width(text: str, font_size: float) -> float:
    """Advance width of ``text`` in user units, without kerning."""
    total = sum(ADVANCES[_resolve(c)] for c in text)
    return total * font_size / UNITS_PER_EM


@lru_cache(maxsize=None)
def _glyph_contours(char: str) -> Tuple[Tuple[Point, ...], ...]:
    """Contours of ``char`` in font units, y up, curves flattened."""
    tokens = _TOKEN.findall(OUTLINES[char])
    contours: List[Contour] = []
    current: Contour = []
    i = 0
    while i < len(tokens):
        command = tokens[i]
        i += 1
        if command == "M":
            if current:
                contours.append(current)
            current = [(float(tokens[i]), float(tokens[i + 1]))]
            i += 2
        elif command == "L":
            current.append((float(tokens[i]), float(tokens[i + 1])))
            i += 2
        elif command == "Q":
            x0, y0 = current[-1]
            cx, cy = float(tokens[i]), float(tokens[i + 1])
            x1, y1 = float(tokens[i + 2]), float(tokens[i + 3])
            i += 4
            for step in range(1, _CURVE_STEPS + 1):
                t = step / _CURVE_STEPS
                u = 1.0 - t
                current.append((
                    u * u * x0 + 2 * u * t * cx + t * t * x1,
                    u * u * y0 + 2 * u * t * cy + t * t * y1,
                ))
        else:
            if current:
                contours.append(current)
            current = []
    if current:
        contours.append(current)
    return tuple(tuple(c) for c in contours)


def text_contours(text: str, x: float, y: float, font_size: float, anchor: str) -> List[Contour]:
    """Filled contours of ``text`` with its baseline origin at ``(x, y)``.

    ``anchor`` is ``"start"``, ``"middle"`` or ``"end"``, as in SVG.
    Coordinates are in user units with y pointing down.
    """
    scale = font_size / UNITS_PER_EM
    width = text_width(text, font_size)
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width

    contours: List[Contour] = []
    pen_x = x
    for char in text:
        char = _resolve(char)
        for contour in _glyph_contours(char):
            contours.append([(pen_x + gx * scale, y - gy * scale) for gx, gy in contour])
        pen_x += ADVANCES[char] * scale
    return contours
