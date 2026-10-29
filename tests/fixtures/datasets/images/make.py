"""Generate the ``images`` dataset: small PNG files and a table naming them, for ``image`` inputs.

Feature 010. Each image is 16 x 16 RGB: dark noise and one bright shape — a filled square, a
horizontal bar or a cross — at a random place in a random bright colour. ``labels.csv`` names each
file, relative to this directory, and its class, the way Ludwig reads images.

The PNG files are written with ``zlib`` and ``struct`` and **stored** rather than compressed, so the
bytes depend on nothing but this script: a compressed stream could differ between zlib builds, and
``tests/unit/test_fixture_datasets.py`` asserts that regenerating gives the same bytes. Only
``randrange`` is used, for the same reason. Principle XI: no model produced any of it.

Run it with ``python tests/fixtures/datasets/images/make.py``; it writes ``labels.csv`` and
``img/`` beside itself.
"""

from __future__ import annotations

import random
import struct
import zlib
from pathlib import Path

SIZE = 16
LABELS = ("square", "bar", "cross")
PER_LABEL = 60
SEED = 20261031


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def png(pixels: list[list[tuple[int, int, int]]]) -> bytes:
    """An 8-bit RGB PNG, filter 0 on every row, stored without compression."""
    height, width = len(pixels), len(pixels[0])
    raw = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in pixels)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 0))
        + _chunk(b"IEND", b"")
    )


def _image(label: str, rng: random.Random) -> list[list[tuple[int, int, int]]]:
    pixels = [
        [(rng.randrange(0, 60), rng.randrange(0, 60), rng.randrange(0, 60)) for _ in range(SIZE)]
        for _ in range(SIZE)
    ]
    colour = (rng.randrange(150, 256), rng.randrange(150, 256), rng.randrange(150, 256))
    if label == "square":
        top, left = rng.randrange(1, SIZE - 7), rng.randrange(1, SIZE - 7)
        cells = [(top + r, left + c) for r in range(6) for c in range(6)]
    elif label == "bar":
        top, left = rng.randrange(1, SIZE - 3), rng.randrange(0, 4)
        cells = [(top + r, left + c) for r in range(2) for c in range(12)]
    else:
        middle_row, middle_col = rng.randrange(4, SIZE - 4), rng.randrange(4, SIZE - 4)
        cells = [(middle_row, middle_col + d) for d in range(-4, 5)]
        cells += [(middle_row + d, middle_col) for d in range(-4, 5)]
    for row, column in cells:
        pixels[row][column] = colour
    return pixels


def generate(root: Path) -> None:
    rng = random.Random(SEED)
    (root / "img").mkdir(exist_ok=True)
    lines = ["image,label"]
    number = 0
    for _ in range(PER_LABEL):
        for label in LABELS:
            name = f"img/{number:04d}.png"
            (root / name).write_bytes(png(_image(label, rng)))
            lines.append(f"{name},{label}")
            number += 1
    (root / "labels.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate(Path(__file__).parent)
