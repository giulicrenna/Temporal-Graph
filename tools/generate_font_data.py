"""Regenerate ``temporal_graph/_font_data.py`` and ``temporal_graph/_colors.py``.

Glyph outlines come from DejaVu Sans and the CSS color names from matplotlib,
both of which ship with matplotlib. Only maintainers need this script; the
generated modules are committed and have no runtime dependencies.

    pip install matplotlib
    python tools/generate_font_data.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

import matplotlib
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from matplotlib.colors import CSS4_COLORS, to_rgb

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "temporal_graph"
FONT_PATH = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf")

CODE_POINTS = (
    list(range(0x20, 0x7F))
    + list(range(0xA0, 0x100))
    + [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x2212]
)


class _CommandPen(BasePen):
    def __init__(self, glyph_set) -> None:
        super().__init__(glyph_set)
        self.commands: List[str] = []

    @staticmethod
    def _fmt(point: Tuple[float, float]) -> str:
        return f"{round(point[0])} {round(point[1])}"

    def _moveTo(self, pt) -> None:
        self.commands.append("M" + self._fmt(pt))

    def _lineTo(self, pt) -> None:
        self.commands.append("L" + self._fmt(pt))

    def _qCurveToOne(self, pt1, pt2) -> None:
        self.commands.append("Q" + self._fmt(pt1) + " " + self._fmt(pt2))

    def _curveToOne(self, pt1, pt2, pt3) -> None:
        raise ValueError("cubic curves are not expected in a TrueType font")

    def _closePath(self) -> None:
        self.commands.append("Z")

    def _endPath(self) -> None:
        self.commands.append("Z")


def build_font_module() -> str:
    font = TTFont(FONT_PATH)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    units_per_em = font["head"].unitsPerEm

    lines = [
        '"""Glyph outlines for the built-in PNG text renderer. Generated file.',
        "",
        "Derived from DejaVu Sans (Bitstream Vera license, see THIRD_PARTY_NOTICES.md).",
        "Regenerate with tools/generate_font_data.py; do not edit by hand.",
        '"""',
        "",
        "from typing import Dict",
        "",
        f"UNITS_PER_EM = {units_per_em}",
        "",
        "ADVANCES: Dict[str, int] = {",
    ]
    outlines = []
    for code in CODE_POINTS:
        name = cmap.get(code)
        if name is None:
            continue
        advance = font["hmtx"][name][0]
        pen = _CommandPen(glyph_set)
        glyph_set[name].draw(pen)
        lines.append(f"    {chr(code)!r}: {advance},")
        outlines.append(f"    {chr(code)!r}: {''.join(pen.commands)!r},")
    lines += ["}", "", "OUTLINES: Dict[str, str] = {", *outlines, "}", ""]
    return "\n".join(lines)


def build_colors_module() -> str:
    lines = [
        '"""CSS named colors. Generated file; see tools/generate_font_data.py."""',
        "",
        "from typing import Dict, Tuple",
        "",
        "NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {",
    ]
    for name in sorted(CSS4_COLORS):
        r, g, b = (round(c * 255) for c in to_rgb(CSS4_COLORS[name]))
        lines.append(f"    {name!r}: ({r}, {g}, {b}),")
    lines += ["}", ""]
    return "\n".join(lines)


def main() -> None:
    (PACKAGE_DIR / "_font_data.py").write_text(build_font_module(), encoding="utf-8")
    (PACKAGE_DIR / "_colors.py").write_text(build_colors_module(), encoding="utf-8")
    print("wrote _font_data.py and _colors.py")


if __name__ == "__main__":
    main()
