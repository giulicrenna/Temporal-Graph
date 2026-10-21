"""The :class:`Figure` returned by :func:`temporal_graph.render`."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Optional, Union

from ._raster import render_png

SUPPORTED_FORMATS = ("svg", "png")
DEFAULT_PNG_SCALE = 2.0

PathLike = Union[str, "os.PathLike[str]"]


class Figure:
    """A rendered temporal graph that can be saved as SVG or PNG.

    Both formats are produced natively, without external libraries.
    """

    def __init__(self, root: ET.Element) -> None:
        self._root = root

    @property
    def width(self) -> float:
        """Width in SVG user units (pixels at ``scale=1``)."""
        return float(self._root.get("width", "0"))

    @property
    def height(self) -> float:
        """Height in SVG user units (pixels at ``scale=1``)."""
        return float(self._root.get("height", "0"))

    def to_svg(self) -> str:
        """Return the figure as an SVG document."""
        body = ET.tostring(self._root, encoding="unicode")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + body

    def to_png_bytes(self, scale: float = DEFAULT_PNG_SCALE) -> bytes:
        """Rasterize the figure to PNG bytes at ``scale`` pixels per user unit."""
        return render_png(self._root, scale)

    def savefig(
        self,
        path: PathLike,
        format: Optional[str] = None,
        scale: float = DEFAULT_PNG_SCALE,
    ) -> str:
        """Save the figure and return the absolute path written.

        The format is taken from ``format`` or, if omitted, from the file
        extension (``.svg`` or ``.png``). ``scale`` only affects PNG output.
        """
        abs_path = os.path.abspath(os.fspath(path))
        kind = (format or os.path.splitext(abs_path)[1].lstrip(".")).lower()
        if kind not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format {kind!r}; use one of {', '.join(SUPPORTED_FORMATS)}"
            )
        data = self.to_svg().encode("utf-8") if kind == "svg" else self.to_png_bytes(scale)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as fh:
            fh.write(data)
        return abs_path

    def _repr_svg_(self) -> str:
        return self.to_svg()

    def __repr__(self) -> str:
        return f"Figure({self.width:g}x{self.height:g})"
