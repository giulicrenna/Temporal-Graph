"""Minimal PNG reader for tests (supports the filter-0 RGB files we write)."""

import struct
import zlib
from typing import List, Tuple

Pixel = Tuple[int, int, int]
SIGNATURE = b"\x89PNG\r\n\x1a\n"


class Image:
    def __init__(self, width: int, height: int, rows: List[bytes]) -> None:
        self.width = width
        self.height = height
        self.rows = rows

    def pixel(self, x: int, y: int) -> Pixel:
        row = self.rows[y]
        return (row[x * 3], row[x * 3 + 1], row[x * 3 + 2])

    def count(self, color: Pixel, tolerance: int = 12) -> int:
        total = 0
        for row in self.rows:
            for x in range(self.width):
                if all(abs(row[x * 3 + c] - color[c]) <= tolerance for c in range(3)):
                    total += 1
        return total

    def non_white(self, x0: int, y0: int, x1: int, y1: int) -> int:
        total = 0
        for y in range(y0, y1):
            row = self.rows[y]
            for x in range(x0, x1):
                if row[x * 3:x * 3 + 3] != b"\xff\xff\xff":
                    total += 1
        return total


def decode_png(data: bytes) -> Image:
    assert data[:8] == SIGNATURE
    position = 8
    header = b""
    idat = b""
    while position < len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        body = data[position + 8:position + 8 + length]
        crc = struct.unpack(">I", data[position + 8 + length:position + 12 + length])[0]
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF
        if kind == b"IHDR":
            header = body
        elif kind == b"IDAT":
            idat += body
        position += 12 + length

    width, height, depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", header)
    assert (depth, color_type) == (8, 2)
    raw = zlib.decompress(idat)
    stride = width * 3
    rows = []
    for y in range(height):
        start = y * (stride + 1)
        assert raw[start] == 0
        rows.append(raw[start + 1:start + 1 + stride])
    return Image(width, height, rows)
