import io
import random

import pytest

from temporal_graph._gif import build_palette, encode_gif

Image = pytest.importorskip("PIL.Image")


def noise_frames(colors, width=301, height=257, count=2, seed=1):
    rng = random.Random(seed)
    palette = list(dict.fromkeys(
        (rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(colors)
    ))
    frames = []
    for _ in range(count):
        pixels = [rng.choice(palette) for _ in range(width * height)]
        frames.append((width, height, bytes(v for p in pixels for v in p)))
    return frames


@pytest.mark.parametrize("colors", [1, 2, 3, 16, 256])
def test_exact_round_trip_through_independent_decoder(colors):
    frames = noise_frames(colors)
    image = Image.open(io.BytesIO(encode_gif(frames, delay_cs=25)))
    assert image.n_frames == len(frames)
    for i, (width, height, rgb) in enumerate(frames):
        image.seek(i)
        assert image.size == (width, height)
        assert image.convert("RGB").tobytes() == rgb


def test_timing_and_loop_metadata():
    frames = noise_frames(4, width=8, height=8, count=3)
    image = Image.open(io.BytesIO(encode_gif(frames, delay_cs=12, loop=3)))
    assert image.info["duration"] == 120
    assert image.info["loop"] == 3


def test_file_structure():
    data = encode_gif(noise_frames(2, width=4, height=4, count=1), delay_cs=10)
    assert data.startswith(b"GIF89a")
    assert data.endswith(b"\x3b")
    assert b"NETSCAPE2.0" in data


def test_palette_is_exact_for_few_colors():
    histogram = {(1, 2, 3): 10, (255, 255, 255): 50}
    palette, mapping = build_palette(histogram)
    assert palette == [(255, 255, 255), (1, 2, 3)]
    assert mapping == {(255, 255, 255): 0, (1, 2, 3): 1}


def test_palette_median_cut_keeps_dominant_colors():
    rng = random.Random(0)
    histogram = {(rng.randrange(256), rng.randrange(256), rng.randrange(256)): 1
                 for _ in range(5000)}
    histogram[(214, 39, 40)] = 100_000
    histogram[(255, 255, 255)] = 500_000
    palette, mapping = build_palette(histogram)
    assert len(palette) == 256
    assert set(mapping) == set(histogram)
    assert palette[mapping[(214, 39, 40)]] == (214, 39, 40)
    assert palette[mapping[(255, 255, 255)]] == (255, 255, 255)


def test_quantized_image_decodes():
    rng = random.Random(2)
    rgb = bytes(rng.randrange(256) for _ in range(64 * 32 * 3))
    image = Image.open(io.BytesIO(encode_gif([(64, 32, rgb)], delay_cs=10)))
    assert image.size == (64, 32)
    assert len(image.convert("RGB").getcolors(100_000)) <= 256


def test_encode_errors():
    with pytest.raises(ValueError, match="At least one frame"):
        encode_gif([], delay_cs=10)
    with pytest.raises(ValueError, match="same size"):
        encode_gif([(2, 2, b"\0" * 12), (3, 2, b"\0" * 18)], delay_cs=10)
