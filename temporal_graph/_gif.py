"""Pure-Python animated GIF encoder (median-cut palette + LZW)."""

from __future__ import annotations

import struct
from collections import Counter
from typing import Dict, Iterator, List, Sequence, Tuple

RGB = Tuple[int, int, int]
Frame = Tuple[int, int, bytes]  # width, height, packed RGB bytes

MAX_COLORS = 256
MAX_LZW_CODE = 4096
SUB_BLOCK_SIZE = 255


def _pixels(rgb: bytes) -> Iterator[RGB]:
    return zip(rgb[0::3], rgb[1::3], rgb[2::3])



# Palette


def build_palette(histogram: Dict[RGB, int]) -> Tuple[List[RGB], Dict[RGB, int]]:
    """Return ``(palette, index_of_color)`` with at most 256 entries.

    Exact when there are few enough colors; otherwise median cut weighted by
    pixel count, so dominant (flat) colors keep their exact value.
    """
    if len(histogram) <= MAX_COLORS:
        exact = sorted(histogram, key=lambda c: (-histogram[c], c))
        return exact, {color: i for i, color in enumerate(exact)}

    boxes: List[List[Tuple[RGB, int]]] = [sorted(histogram.items())]
    while len(boxes) < MAX_COLORS:
        index, channel = _box_to_split(boxes)
        if index < 0:
            break
        box = sorted(boxes[index], key=lambda item: item[0][channel])
        half = sum(count for _, count in box) / 2
        running = 0
        cut = 1
        for i, (_, count) in enumerate(box[:-1]):
            running += count
            cut = i + 1
            if running >= half:
                break
        boxes[index:index + 1] = [box[:cut], box[cut:]]

    palette: List[RGB] = []
    mapping: Dict[RGB, int] = {}
    for i, box in enumerate(boxes):
        total = sum(count for _, count in box)
        red, green, blue = (
            round(sum(color[c] * count for color, count in box) / total) for c in range(3)
        )
        palette.append((red, green, blue))
        for color, _ in box:
            mapping[color] = i
    return palette, mapping


def _box_to_split(boxes: Sequence[Sequence[Tuple[RGB, int]]]) -> Tuple[int, int]:
    """Index and channel of the box with the largest population-weighted range."""
    best_index, best_channel, best_score = -1, 0, 0
    for index, box in enumerate(boxes):
        if len(box) < 2:
            continue
        population = sum(count for _, count in box)
        for channel in range(3):
            values = [color[channel] for color, _ in box]
            score = (max(values) - min(values)) * population
            if score > best_score:
                best_index, best_channel, best_score = index, channel, score
    return best_index, best_channel



# LZW


def lzw_encode(indices: bytes, min_code_size: int) -> bytes:
    """GIF-flavoured variable-width LZW, packed least-significant bit first."""
    clear_code = 1 << min_code_size
    end_code = clear_code + 1
    out = bytearray()
    buffer = 0
    bits = 0
    code_size = min_code_size + 1

    def emit(code: int) -> None:
        nonlocal buffer, bits
        buffer |= code << bits
        bits += code_size
        while bits >= 8:
            out.append(buffer & 0xFF)
            buffer >>= 8
            bits -= 8

    table: Dict[int, int] = {}
    next_code = end_code + 1
    emit(clear_code)
    prefix = indices[0]
    for symbol in indices[1:]:
        key = (prefix << 8) | symbol
        code = table.get(key)
        if code is not None:
            prefix = code
            continue
        emit(prefix)
        if next_code < MAX_LZW_CODE:
            table[key] = next_code
            next_code += 1
            # The decoder lags one entry behind, so widen only once the
            # table has grown past the current width.
            if next_code > (1 << code_size):
                code_size += 1
        else:
            emit(clear_code)
            table.clear()
            next_code = end_code + 1
            code_size = min_code_size + 1
        prefix = symbol
    emit(prefix)
    emit(end_code)
    if bits:
        out.append(buffer & 0xFF)
    return bytes(out)


def _sub_blocks(data: bytes) -> bytes:
    out = bytearray()
    for start in range(0, len(data), SUB_BLOCK_SIZE):
        chunk = data[start:start + SUB_BLOCK_SIZE]
        out.append(len(chunk))
        out += chunk
    out.append(0)
    return bytes(out)



# File


def encode_gif(frames: Sequence[Frame], delay_cs: int, loop: int = 0) -> bytes:
    """Encode same-sized RGB frames as an animated GIF.

    ``delay_cs`` is the per-frame delay in hundredths of a second. ``loop`` is
    the NETSCAPE repeat count; 0 loops forever.
    """
    if not frames:
        raise ValueError("At least one frame is required")
    width, height, _ = frames[0]
    if any((w, h) != (width, height) for w, h, _ in frames):
        raise ValueError("All frames must have the same size")

    histogram: Counter[RGB] = Counter()
    for _, _, rgb in frames:
        histogram.update(_pixels(rgb))
    palette, mapping = build_palette(histogram)

    color_bits = max(1, (len(palette) - 1).bit_length())
    table_size = 1 << color_bits
    color_table = b"".join(bytes(c) for c in palette) + b"\x00" * 3 * (table_size - len(palette))
    min_code_size = max(2, color_bits)

    out = bytearray(b"GIF89a")
    out += struct.pack("<HHBBB", width, height, 0xF0 | (color_bits - 1), 0, 0)
    out += color_table
    out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01" + struct.pack("<H", loop) + b"\x00"
    for _, _, rgb in frames:
        out += b"\x21\xf9\x04\x04" + struct.pack("<H", delay_cs) + b"\x00\x00"
        out += b"\x2c" + struct.pack("<HHHHB", 0, 0, width, height, 0)
        indices = bytes(mapping[pixel] for pixel in _pixels(rgb))
        out.append(min_code_size)
        out += _sub_blocks(lzw_encode(indices, min_code_size))
    out.append(0x3B)
    return bytes(out)
